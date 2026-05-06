"""
Live detection API endpoints for real-time camera feeds.
Processes individual frames using the full detection pipeline including
BehaviorAnalyzer for accurate suspicion scoring and alert generation.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import cv2
import numpy as np
import base64
import time
from typing import Dict

from app.database import get_db
from app.services.person_detector import PersonDetector
from app.services.product_detector import ProductDetector
from app.services.person_tracker import PersonTracker
from app.services.pose_estimator import PoseEstimator
from app.services.interaction_detector import InteractionDetector
from app.services.behavior_analyzer import BehaviorAnalyzer
from app.services.alert_generator import AlertGenerator
from app.config import settings

router = APIRouter()

# ---------------------------------------------------------------------------
# Singleton detectors (stateless, shared across all sessions)
# ---------------------------------------------------------------------------
person_detector = PersonDetector()
product_detector = ProductDetector(model=person_detector.model)
pose_estimator = PoseEstimator()
interaction_detector = InteractionDetector()
alert_generator = AlertGenerator()

# ---------------------------------------------------------------------------
# Per-session state
# Sessions are keyed by session_id supplied by the frontend.
# Stale sessions (idle > 5 min) are evicted automatically.
# ---------------------------------------------------------------------------
_SESSION_TTL_SECONDS = 300


class _LiveSession:
    def __init__(self):
        self.tracker = PersonTracker(
            iou_threshold=0.2, max_age=30, max_center_distance=110.0
        )
        self.behavior_analyzers: Dict[int, BehaviorAnalyzer] = {}
        self.frame_number: int = 0
        self.last_seen: float = time.time()
        self.pose_frame_counter: int = 0
        self.last_landmarks_by_track_id: Dict[int, Dict] = {}

    def touch(self):
        self.last_seen = time.time()

    @property
    def is_stale(self) -> bool:
        return (time.time() - self.last_seen) > _SESSION_TTL_SECONDS


_sessions: Dict[str, _LiveSession] = {}


def _get_or_create_session(session_id: str) -> _LiveSession:
    """Return existing session or create a new one. Evict stale sessions."""
    stale = [sid for sid, s in _sessions.items() if s.is_stale]
    for sid in stale:
        del _sessions[sid]

    if session_id not in _sessions:
        _sessions[session_id] = _LiveSession()

    session = _sessions[session_id]
    session.touch()
    return session


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class DetectionRequest(BaseModel):
    image: str                    # Base64-encoded JPEG/PNG frame
    session_id: str = "default"  # Stable ID for the duration of a camera session


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/detect-frame-base64")
async def detect_frame_base64(
    data: DetectionRequest, db: Session = Depends(get_db)
):
    """
    Process a single base64-encoded camera frame through the full pipeline:
    person detection -> tracking -> pose estimation -> interaction detection
    -> behavior analysis -> alert generation.

    Supply a stable ``session_id`` for the duration of a camera session so
    that per-person BehaviorAnalyzer state is maintained across frames.
    """
    try:
        # 1. Decode image
        image_data = data.image
        if "," in image_data:
            image_data = image_data.split(",")[1]

        img_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            raise HTTPException(status_code=400, detail="Invalid image data")

        # 2. Session state
        session = _get_or_create_session(data.session_id)
        frame_number = session.frame_number
        session.frame_number += 1
        timestamp = frame_number / settings.video_processing_fps

        # 3. Person detection + tracking
        persons = person_detector.detect_persons(frame)
        products = product_detector.detect_products(frame)
        tracked_persons = session.tracker.update(persons)

        # 4. Per-person: pose -> interaction -> behavior
        pose_stride = max(1, settings.pose_estimation_interval)
        detections = []

        for person in tracked_persons:
            track_id = person.get("track_id")
            bbox = person["bbox"]
            x1, y1, x2, y2 = map(int, bbox)

            if x2 <= x1 or y2 <= y1:
                continue

            # Pose estimation with stride caching
            use_cached = (
                track_id is not None
                and (session.pose_frame_counter % pose_stride != 0)
                and track_id in session.last_landmarks_by_track_id
            )

            landmarks = (
                session.last_landmarks_by_track_id[track_id]
                if use_cached
                else pose_estimator.estimate_pose(frame, person)
            )

            pose_detected = landmarks is not None
            if pose_detected and track_id is not None:
                session.last_landmarks_by_track_id[track_id] = landmarks

            zone = "neutral"
            left_action = "idle"
            right_action = "idle"
            suspicion_score = 0

            if pose_detected:
                try:
                    interaction = interaction_detector.detect_interaction(
                        landmarks=landmarks, person=person
                    )
                    zone = interaction.get("primary_zone", "neutral")
                    left_action = interaction.get("left_hand", {}).get("action", "idle")
                    right_action = interaction.get("right_hand", {}).get("action", "idle")

                    if track_id is not None:
                        if track_id not in session.behavior_analyzers:
                            session.behavior_analyzers[track_id] = BehaviorAnalyzer()

                        analyzer = session.behavior_analyzers[track_id]
                        analyzer.analyze_frame(
                            frame_number, timestamp, person, landmarks, interaction
                        )
                        suspicion_score = analyzer.get_current_suspicion_score()

                        # Emit only sequences that have fully ended (score dropped)
                        new_alerts = analyzer.flush_completed_alerts()
                        for alert_data in new_alerts:
                            try:
                                await alert_generator.create_live_alert(alert_data, db)
                            except Exception as ae:
                                print(f"Alert creation failed: {ae}")

                except Exception as e:
                    print(f"Interaction/behavior error for track {track_id}: {e}")

            detections.append({
                "person": {
                    "bbox": bbox,
                    "confidence": round(person["confidence"], 2),
                    "track_id": track_id,
                },
                "pose": {"detected": pose_detected},
                "interaction": {
                    "zone": zone,
                    "left_hand_action": left_action,
                    "right_hand_action": right_action,
                    "nearby_products": len(products),
                },
                "suspicion_score": suspicion_score,
                "suspicious": suspicion_score >= settings.suspicion_score_threshold,
            })

        session.pose_frame_counter += 1

        return {
            "success": True,
            "detections": detections,
            "person_count": len(tracked_persons),
            "product_count": len(products),
            "frame_number": frame_number,
            "has_suspicious_activity": any(d["suspicious"] for d in detections),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


@router.delete("/session/{session_id}")
async def end_session(session_id: str):
    """
    Explicitly end a live detection session and release its state.
    Call this when the user stops the camera feed.
    """
    _sessions.pop(session_id, None)
    return {"message": f"Session '{session_id}' ended"}
