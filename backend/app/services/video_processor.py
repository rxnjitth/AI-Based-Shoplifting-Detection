"""
Video Input Layer - OpenCV-based video capture and frame extraction.
Handles video file processing and frame preprocessing.
"""
import cv2
import numpy as np
from typing import Generator, Tuple, Optional, Dict
import os

from app.config import settings


class VideoProcessor:
    """
    Processes video files and extracts frames for analysis.
    Implements Layer 1: Video Input Layer.
    """
    
    def __init__(self, target_fps: Optional[int] = None):
        """
        Initialize video processor.
        
        Args:
            target_fps: Target frame rate for processing. Defaults to config setting.
        """
        self.target_fps = target_fps or settings.video_processing_fps
        self.current_video_path = None
        self.video_metadata = {}
    
    def get_video_metadata(self, video_path: str) -> Dict:
        """
        Extract metadata from video file.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary containing video metadata
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")
        
        metadata = {
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "duration_seconds": 0,
            "codec": int(cap.get(cv2.CAP_PROP_FOURCC))
        }

        if metadata["fps"] and metadata["fps"] > 0:
            metadata["duration_seconds"] = int(metadata["total_frames"] / metadata["fps"])
        
        cap.release()
        return metadata
    
    def preprocess_frame(self, frame: np.ndarray, target_size: Tuple[int, int] = (640, 640)) -> np.ndarray:
        """
        Preprocess frame for detection models.
        
        Args:
            frame: Input frame
            target_size: Target size for resizing
            
        Returns:
            Preprocessed frame
        """
        # Check if resize is needed (optimization)
        if frame.shape[1] == target_size[0] and frame.shape[0] == target_size[1]:
            return frame
        # Use INTER_AREA for downscaling (faster and better quality)
        interpolation = cv2.INTER_AREA if frame.shape[0] > target_size[1] else cv2.INTER_LINEAR
        resized = cv2.resize(frame, target_size, interpolation=interpolation)
        return resized
    
    def extract_frames(self, video_path: str) -> Generator[Tuple[int, np.ndarray, float], None, None]:
        """
        Extract frames from video at specified FPS.
        
        Args:
            video_path: Path to video file
            
        Yields:
            Tuple of (frame_number, frame, timestamp_seconds)
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        self.current_video_path = video_path
        self.video_metadata = self.get_video_metadata(video_path)
        
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")
        
        original_fps = cap.get(cv2.CAP_PROP_FPS)
        if original_fps <= 0:
            original_fps = float(self.target_fps)

        frame_interval = max(1, int(original_fps / self.target_fps))
        
        frame_number = 0
        processed_count = 0
        
        print(f"📹 Processing video: {os.path.basename(video_path)}")
        print(f"📊 Original FPS: {original_fps:.2f}, Processing every {frame_interval} frames")
        
        while True:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Process frames at target FPS interval
            if frame_number % frame_interval == 0:
                timestamp = frame_number / original_fps
                yield frame_number, frame, timestamp
                processed_count += 1
            
            frame_number += 1
        
        cap.release()
        print(f"✅ Processed {processed_count} frames from {frame_number} total frames")
    
    async def process_video(self, video_path: str, db_session, output_path: Optional[str] = None):
        """
        Main processing pipeline for a video file.
        Coordinates all detection layers and generates annotated video.
        
        Args:
            video_path: Path to video file
            db_session: Database session for storing results
        """
        from app.services.person_detector import PersonDetector
        from app.services.product_detector import ProductDetector
        from app.services.person_tracker import PersonTracker
        from app.services.pose_estimator import PoseEstimator
        from app.services.interaction_detector import InteractionDetector
        from app.services.behavior_analyzer import BehaviorAnalyzer
        from app.services.alert_generator import AlertGenerator
        from app.services.visualizer import DetectionVisualizer
        
        # Initialize detection pipeline
        person_detector = PersonDetector()
        product_detector = ProductDetector(model=person_detector.model)
        person_tracker = PersonTracker(iou_threshold=0.2, max_age=30, max_center_distance=110.0)
        pose_estimator = PoseEstimator()
        interaction_detector = InteractionDetector()
        behavior_analyzers: Dict[int, BehaviorAnalyzer] = {}
        alert_generator = AlertGenerator()
        visualizer = DetectionVisualizer()
        pose_stride = max(1, settings.pose_estimation_interval)
        last_landmarks_by_track_id: Dict[int, Dict] = {}
        
        # Setup output video writer.
        # Write to a temporary path first so clients don't consume a partial file.
        metadata = self.get_video_metadata(video_path)
        if output_path is None:
            base_path, _ = os.path.splitext(video_path)
            output_path = f"{base_path}_annotated.mp4"

        output_base, output_ext = os.path.splitext(output_path)
        temp_output_path = f"{output_base}.processing{output_ext or '.mp4'}"

        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)

        if os.path.exists(output_path):
            os.remove(output_path)

        # Use H.264 for browser-compatible playback in HTML5 video.
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        out = cv2.VideoWriter(
            temp_output_path,
            fourcc,
            self.target_fps,
            (metadata["width"], metadata["height"])
        )

        if not out.isOpened():
            raise RuntimeError(
                "Failed to initialize H.264 video writer (avc1). "
                "Install/enable OpenH264 support in OpenCV environment."
            )
        
        print(f"🚀 Starting video processing pipeline...")
        print(f"💾 Saving annotated video to: {output_path}")
        
        # Process each frame
        for frame_number, frame, timestamp in self.extract_frames(video_path):
            # Layer 2: Person Detection
            persons = person_detector.detect_persons(frame)
            products = product_detector.detect_products(frame)
            tracked_persons = person_tracker.update(persons)
            
            interactions_list = []
            landmarks_list = []
            
            if tracked_persons:
                # Process each detected person
                for person in tracked_persons:
                    track_id = person.get("track_id")
                    use_cached_landmarks = (
                        track_id is not None
                        and (frame_number % pose_stride != 0)
                        and track_id in last_landmarks_by_track_id
                    )

                    # Layer 3: Pose Estimation
                    if use_cached_landmarks:
                        landmarks = last_landmarks_by_track_id[track_id]
                    else:
                        landmarks = pose_estimator.estimate_pose(frame, person)
                    
                    if landmarks is None:
                        landmarks_list.append(None)
                        continue
                    
                    landmarks_list.append(landmarks)

                    if track_id is not None:
                        last_landmarks_by_track_id[track_id] = landmarks
                    
                    # Layer 4: Human-Object Interaction
                    interaction = interaction_detector.detect_interaction(landmarks, person)
                    if interaction:
                        interactions_list.append(interaction)

                    if track_id is None:
                        continue

                    analyzer = behavior_analyzers.get(track_id)
                    if analyzer is None:
                        analyzer = BehaviorAnalyzer()
                        behavior_analyzers[track_id] = analyzer
                    
                    # Layer 5: Behavior Analysis
                    analyzer.analyze_frame(
                        frame_number,
                        timestamp,
                        person,
                        landmarks,
                        interaction
                    )
            
            # Draw visualizations on frame
            current_scores = [analyzer.get_current_suspicion_score() for analyzer in behavior_analyzers.values()]
            suspicion_score = max(current_scores) if current_scores else 0
            is_suspicious = suspicion_score >= settings.suspicion_score_threshold
            
            annotated_frame = visualizer.draw_detections(
                frame,
                tracked_persons or [],
                landmarks_list,
                products,
                interactions_list,
                frame_number,
                is_suspicious,
                suspicion_score
            )
            
            # Write annotated frame
            out.write(annotated_frame)
        
        # Release writer before publishing final output.
        out.release()

        # Publish final annotated video atomically.
        os.replace(temp_output_path, output_path)
        
        # Generate alerts from all tracked persons.
        alerts = []
        for analyzer in behavior_analyzers.values():
            alerts.extend(analyzer.generate_alerts())
        
        # Layer 6: Alert Generation with Evidence
        for alert_data in alerts:
            await alert_generator.create_alert(
                video_path,
                alert_data,
                self,
                db_session
            )
        
        print(f"✅ Pipeline complete. Generated {len(alerts)} alerts")
        print(f"🎬 Annotated video saved: {output_path}")
