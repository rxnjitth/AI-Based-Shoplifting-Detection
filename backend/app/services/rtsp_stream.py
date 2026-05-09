"""
RTSP Stream Service - pulls frames from an EZVIZ (or any RTSP) camera
and runs them through the full detection pipeline.

EZVIZ RTSP URL format:
  rtsp://<username>:<password>@<camera_ip>:<port>/h264/ch1/main/av_stream
  Default port: 554
  Default sub-stream (lower res, faster): /h264/ch1/sub/av_stream
"""
import asyncio
import threading
import time
import cv2
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from app.config import settings


class StreamStatus(str, Enum):
    IDLE = "idle"
    CONNECTING = "connecting"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class StreamState:
    status: StreamStatus = StreamStatus.IDLE
    error: Optional[str] = None
    frames_processed: int = 0
    alerts_generated: int = 0
    fps: float = 0.0
    last_frame_time: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    # Latest JPEG bytes for the preview endpoint
    latest_frame_jpg: Optional[bytes] = None


class RTSPStreamManager:
    """
    Manages one RTSP camera stream per camera_id.
    Runs frame capture + detection in a background thread.
    Alert generation is dispatched back to the async event loop.
    """

    def __init__(self):
        self._streams: Dict[str, "_StreamWorker"] = {}

    def start(
        self,
        camera_id: str,
        rtsp_url: str,
        on_alert: Callable,          # async coroutine called with (alert_data, db)
        get_db_session: Callable,    # callable returning a DB session
    ) -> StreamState:
        if camera_id in self._streams:
            worker = self._streams[camera_id]
            if worker.state.status == StreamStatus.RUNNING:
                return worker.state
            # Clean up stale worker
            worker.stop()

        worker = _StreamWorker(camera_id, rtsp_url, on_alert, get_db_session)
        self._streams[camera_id] = worker
        worker.start()
        return worker.state

    def stop(self, camera_id: str) -> bool:
        worker = self._streams.pop(camera_id, None)
        if worker:
            worker.stop()
            return True
        return False

    def get_state(self, camera_id: str) -> Optional[StreamState]:
        worker = self._streams.get(camera_id)
        return worker.state if worker else None

    def list_cameras(self) -> Dict[str, StreamState]:
        return {cid: w.state for cid, w in self._streams.items()}

    def get_latest_frame(self, camera_id: str) -> Optional[bytes]:
        worker = self._streams.get(camera_id)
        if worker:
            return worker.state.latest_frame_jpg
        return None


class _StreamWorker:
    """Background thread that reads RTSP frames and runs detection."""

    def __init__(self, camera_id, rtsp_url, on_alert, get_db_session):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.on_alert = on_alert
        self.get_db_session = get_db_session
        self.state = StreamState()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        # Grab the running event loop so we can schedule async alert saves
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = None

    def start(self):
        self.state.status = StreamStatus.CONNECTING
        self.state.started_at = time.time()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self.state.status = StreamStatus.STOPPED

    def _run(self):
        # Import here to avoid circular imports at module load time
        from app.services.person_detector import PersonDetector
        from app.services.product_detector import ProductDetector
        from app.services.person_tracker import PersonTracker
        from app.services.pose_estimator import PoseEstimator
        from app.services.interaction_detector import InteractionDetector
        from app.services.behavior_analyzer import BehaviorAnalyzer

        # Each worker gets its own detector instances (thread safety)
        person_detector = PersonDetector()
        product_detector = ProductDetector(model=person_detector.model)
        pose_estimator = PoseEstimator()
        interaction_detector = InteractionDetector()
        tracker = PersonTracker(iou_threshold=0.2, max_age=30, max_center_distance=110.0)
        behavior_analyzers: Dict[int, BehaviorAnalyzer] = {}
        last_landmarks: Dict[int, Dict] = {}

        # Open RTSP stream
        cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        # Reduce internal buffer to get near-realtime frames
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            self.state.status = StreamStatus.ERROR
            self.state.error = f"Cannot open RTSP stream: {self.rtsp_url}"
            return

        self.state.status = StreamStatus.RUNNING
        target_interval = 1.0 / settings.video_processing_fps
        pose_stride = max(1, settings.pose_estimation_interval)
        pose_counter = 0
        frame_number = 0
        fps_counter = 0
        fps_timer = time.time()

        while not self._stop_event.is_set():
            loop_start = time.time()

            ret, frame = cap.read()
            if not ret:
                # Try to reconnect once
                cap.release()
                time.sleep(2)
                cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if not cap.isOpened():
                    self.state.status = StreamStatus.ERROR
                    self.state.error = "RTSP stream disconnected"
                    break
                continue

            timestamp = frame_number / settings.video_processing_fps

            # --- Detection pipeline ---
            persons = person_detector.detect_persons(frame)
            products = product_detector.detect_products(frame)
            tracked = tracker.update(persons)

            for person in tracked:
                track_id = person.get("track_id")
                bbox = person["bbox"]
                x1, y1, x2, y2 = map(int, bbox)
                if x2 <= x1 or y2 <= y1:
                    continue

                use_cached = (
                    track_id is not None
                    and (pose_counter % pose_stride != 0)
                    and track_id in last_landmarks
                )
                landmarks = (
                    last_landmarks[track_id]
                    if use_cached
                    else pose_estimator.estimate_pose(frame, person)
                )

                if landmarks is None:
                    continue

                if track_id is not None:
                    last_landmarks[track_id] = landmarks

                try:
                    interaction = interaction_detector.detect_interaction(
                        landmarks=landmarks, person=person
                    )

                    if track_id is not None:
                        if track_id not in behavior_analyzers:
                            behavior_analyzers[track_id] = BehaviorAnalyzer()

                        analyzer = behavior_analyzers[track_id]
                        analyzer.analyze_frame(
                            frame_number, timestamp, person, landmarks, interaction
                        )

                        completed = analyzer.flush_completed_alerts()
                        for alert_data in completed:
                            self.state.alerts_generated += 1
                            self._dispatch_alert(alert_data)

                except Exception as e:
                    print(f"[RTSP:{self.camera_id}] Detection error: {e}")

            pose_counter += 1
            frame_number += 1
            self.state.frames_processed = frame_number

            # Store latest frame as JPEG for preview
            _, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            self.state.latest_frame_jpg = jpg.tobytes()
            self.state.last_frame_time = time.time()

            # FPS tracking
            fps_counter += 1
            if time.time() - fps_timer >= 1.0:
                self.state.fps = fps_counter
                fps_counter = 0
                fps_timer = time.time()

            # Throttle to target FPS
            elapsed = time.time() - loop_start
            sleep_time = target_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        cap.release()
        self.state.status = StreamStatus.STOPPED

    def _dispatch_alert(self, alert_data: dict):
        """Schedule the async alert save on the event loop."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._save_alert(alert_data), self._loop
            )

    async def _save_alert(self, alert_data: dict):
        from app.services.alert_generator import AlertGenerator
        generator = AlertGenerator()
        db = next(self.get_db_session())
        try:
            await generator.create_live_alert(alert_data, db)
        except Exception as e:
            print(f"[RTSP:{self.camera_id}] Alert save failed: {e}")
        finally:
            db.close()


# Global singleton
rtsp_manager = RTSPStreamManager()
