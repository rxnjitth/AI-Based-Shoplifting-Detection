"""
Alert Generation and Evidence Processing.
Implements Layer 6: Alert Generation with snapshots and video clips.
"""
from typing import Dict, Optional
from datetime import datetime
import cv2
import numpy as np
import os
import uuid

from app.config import settings
from app.database import Alert, Event, BehaviorLog, AlertStatus


class AlertGenerator:
    """
    Generates alerts with evidence (snapshots and video clips).
    """
    
    def __init__(self):
        """Initialize alert generator."""
        self.snapshot_dir = settings.evidence_snapshots_dir
        self.clip_dir = settings.evidence_clips_dir
        
        # Ensure directories exist
        os.makedirs(self.snapshot_dir, exist_ok=True)
        os.makedirs(self.clip_dir, exist_ok=True)
    
    async def create_alert(
        self,
        video_path: str,
        alert_data: Dict,
        video_processor,
        db_session
    ):
        """
        Create alert with evidence in database.
        
        Args:
            video_path: Path to source video
            alert_data: Alert data from BehaviorAnalyzer
            video_processor: VideoProcessor instance for frame extraction
            db_session: Database session
        """
        # Generate unique alert ID
        alert_id = str(uuid.uuid4())
        
        # Extract frame for snapshot
        snapshot_path = await self._create_snapshot(
            video_path,
            alert_data["frame_number"],
            alert_data["person_bbox"],
            alert_data["suspicion_score"],
            alert_id
        )

        # Capture a second snapshot near the end of suspicious sequence.
        secondary_frame = alert_data.get("end_frame", alert_data["frame_number"])
        secondary_snapshot_path = await self._create_snapshot(
            video_path,
            secondary_frame,
            alert_data["person_bbox"],
            alert_data["suspicion_score"],
            f"{alert_id}_2"
        )
        
        # Create video clip
        clip_path = await self._create_clip(
            video_path,
            alert_data["timestamp"],
            alert_data["suspicion_score"],
            alert_id
        )
        
        # Create alert record
        alert = Alert(
            timestamp=datetime.utcnow(),
            suspicion_score=alert_data["suspicion_score"],
            reason=alert_data["reason"],
            person_bbox=self._bbox_to_string(alert_data["person_bbox"]),
            video_path=video_path,
            snapshot_path=snapshot_path,
            clip_path=clip_path,
            status=AlertStatus.NEW,
            frame_number=alert_data["frame_number"]
        )
        
        db_session.add(alert)
        db_session.flush()  # Get alert ID
        
        # Create event records for zone transitions
        for transition in alert_data.get("zone_transitions", []):
            event = Event(
                alert_id=alert.id,
                event_type=transition,
                timestamp=datetime.utcnow(),
                event_metadata=f"Duration: {alert_data.get('duration', 0):.2f}s"
            )
            db_session.add(event)

        if secondary_snapshot_path:
            db_session.add(Event(
                alert_id=alert.id,
                event_type="secondary_snapshot",
                timestamp=datetime.utcnow(),
                event_metadata=secondary_snapshot_path,
            ))
        
        db_session.commit()
        
        print(f"🚨 Alert created: ID={alert.id}, Score={alert.suspicion_score:.1f}, Reason={alert.reason}")
    
    async def _create_snapshot(
        self,
        video_path: str,
        frame_number: int,
        bbox: list,
        score: float,
        alert_id: str
    ) -> str:
        """
        Create annotated snapshot from video frame.
        
        Args:
            video_path: Path to video
            frame_number: Frame number to extract
            bbox: Person bounding box
            score: Suspicion score
            alert_id: Unique alert ID
            
        Returns:
            Path to saved snapshot
        """
        # Open video and seek to frame
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print(f"⚠️ Failed to extract frame {frame_number}")
            return None
        
        # Draw bounding box
        x1, y1, x2, y2 = [int(coord) for coord in bbox]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
        
        # Add score annotation
        label = f"Suspicion: {score:.1f}"
        (text_width, text_height), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2
        )
        
        cv2.rectangle(
            frame,
            (x1, y1 - text_height - baseline - 10),
            (x1 + text_width, y1),
            (0, 0, 255),
            -1
        )
        
        cv2.putText(
            frame,
            label,
            (x1, y1 - baseline - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )
        
        # Save snapshot
        snapshot_filename = f"{alert_id}.jpg"
        snapshot_path = os.path.join(self.snapshot_dir, snapshot_filename)
        cv2.imwrite(snapshot_path, frame)
        
        # Return only the filename (not full path) for URL construction
        return snapshot_filename
    
    async def _create_clip(
        self,
        video_path: str,
        timestamp: float,
        score: float,
        alert_id: str
    ) -> str:
        """
        Create video clip around alert timestamp.
        
        Args:
            video_path: Path to source video
            timestamp: Alert timestamp in seconds
            score: Suspicion score
            alert_id: Unique alert ID
            
        Returns:
            Path to saved clip
        """
        # Calculate start and end times
        start_time = max(0, timestamp - settings.clip_duration_before)
        end_time = timestamp + settings.clip_duration_after
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Seek to start
        start_frame = int(start_time * fps)
        end_frame = int(end_time * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        # Setup video writer
        clip_filename = f"{alert_id}.mp4"
        clip_path = os.path.join(self.clip_dir, clip_filename)
        
        # Use H.264 for reliable browser playback.
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        out = cv2.VideoWriter(clip_path, fourcc, fps, (width, height))

        if not out.isOpened():
            cap.release()
            raise RuntimeError(
                "Failed to initialize H.264 clip writer (avc1). "
                "Install/enable OpenH264 support in OpenCV environment."
            )
        
        # Write frames
        frame_count = 0
        max_frames = end_frame - start_frame
        
        while frame_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Add timestamp overlay
            current_time = start_time + (frame_count / fps)
            time_label = f"Time: {current_time:.2f}s | Score: {score:.1f}"
            
            cv2.putText(
                frame,
                time_label,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
            
            out.write(frame)
            frame_count += 1
        
        cap.release()
        out.release()
        
        # Return only the filename (not full path) for URL construction
        return clip_filename
    
    def _bbox_to_string(self, bbox: list) -> str:
        """Convert bounding box to string format."""
        return ",".join([f"{coord:.2f}" for coord in bbox])
