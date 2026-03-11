"""
Visualization Layer - Draws detection results on video frames.
"""
import cv2
import numpy as np
from typing import Dict, List, Optional


class DetectionVisualizer:
    """Visualizes person detection, pose estimation, and alerts on video frames."""
    
    def __init__(self):
        """Initialize visualizer with color scheme."""
        self.colors = {
            "person_box": (0, 255, 0),      # Green
            "alert_box": (0, 0, 255),       # Red
            "product_box": (255, 128, 0),   # Orange
            "pose_point": (255, 0, 255),    # Magenta
            "pose_line": (0, 255, 255),     # Cyan
            "text_bg": (0, 0, 0),           # Black
            "text_fg": (255, 255, 255),     # White
        }
        
        # Pose connections for skeleton visualization
        self.pose_connections = [
            ("left_shoulder", "right_shoulder"),
            ("left_shoulder", "left_elbow"),
            ("right_shoulder", "right_elbow"),
            ("left_elbow", "left_wrist"),
            ("right_elbow", "right_wrist"),
            ("left_shoulder", "left_hip"),
            ("right_shoulder", "right_hip"),
            ("left_hip", "right_hip"),
        ]
    
    def draw_detections(
        self,
        frame: np.ndarray,
        persons: List[Dict],
        landmarks_list: List[Optional[Dict]],
        products: List[Dict],
        interactions: List[Dict],
        frame_number: int,
        is_suspicious: bool = False,
        suspicion_score: int = 0
    ) -> np.ndarray:
        """
        Draw all detection results on frame.
        
        Args:
            frame: Input frame
            persons: List of detected persons
            landmarks_list: List of pose landmarks for each person
            products: List of detected products
            interactions: List of detected interactions
            frame_number: Current frame number
            is_suspicious: Whether suspicious behavior detected
            suspicion_score: Suspicion score (0-100)
            
        Returns:
            Annotated frame
        """
        annotated = frame.copy()
        
        # Draw person bounding boxes and poses
        for i, (person, landmarks) in enumerate(zip(persons, landmarks_list)):
            color = self.colors["alert_box"] if is_suspicious else self.colors["person_box"]
            
            # Draw bounding box
            bbox = person["bbox"]
            x1, y1, x2, y2 = [int(c) for c in bbox]
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Draw confidence
            track_id = person.get("track_id")
            if track_id is not None:
                conf_text = f"ID {track_id}: {person['confidence']:.2f}"
            else:
                conf_text = f"Person {i+1}: {person['confidence']:.2f}"
            self._draw_text(annotated, conf_text, (x1, y1 - 10), color)
            
            # Draw pose landmarks if available
            if landmarks:
                self._draw_pose(annotated, landmarks)
        
        # Draw interaction zones/indicators
        for interaction in interactions:
            self._draw_interaction(annotated, interaction)

        # Draw product detections
        for product in products:
            x1, y1, x2, y2 = [int(c) for c in product["bbox"]]
            cv2.rectangle(annotated, (x1, y1), (x2, y2), self.colors["product_box"], 2)
            label = product.get("label", "product")
            conf = product.get("confidence", 0.0)
            self._draw_text(annotated, f"{label}: {conf:.2f}", (x1, max(20, y1 - 8)), self.colors["product_box"])
        
        # Draw frame info and alerts
        self._draw_frame_info(annotated, frame_number, len(persons))
        self._draw_status(annotated, is_suspicious)
        
        if is_suspicious:
            self._draw_alert(annotated, suspicion_score)
        
        return annotated
    
    def _draw_pose(self, frame: np.ndarray, landmarks: Dict):
        """Draw pose skeleton on frame."""
        # Draw connections (skeleton)
        for start_point, end_point in self.pose_connections:
            if start_point in landmarks and end_point in landmarks:
                start = landmarks[start_point]
                end = landmarks[end_point]
                
                if start["visibility"] > 0.5 and end["visibility"] > 0.5:
                    pt1 = (int(start["x"]), int(start["y"]))
                    pt2 = (int(end["x"]), int(end["y"]))
                    cv2.line(frame, pt1, pt2, self.colors["pose_line"], 2)
        
        # Draw landmark points
        for landmark_name, landmark in landmarks.items():
            if landmark["visibility"] > 0.5:
                pt = (int(landmark["x"]), int(landmark["y"]))
                cv2.circle(frame, pt, 4, self.colors["pose_point"], -1)
                cv2.circle(frame, pt, 5, self.colors["text_fg"], 1)
    
    def _draw_interaction(self, frame: np.ndarray, interaction: Dict):
        """Draw interaction indicator."""
        action = interaction.get("action", "")
        position = interaction.get("position")
        
        if position:
            x, y = int(position[0]), int(position[1])
            
            # Draw interaction marker
            cv2.circle(frame, (x, y), 15, (0, 255, 255), 2)
            
            # Draw action text
            self._draw_text(frame, action, (x + 20, y), (0, 255, 255))
    
    def _draw_frame_info(self, frame: np.ndarray, frame_number: int, person_count: int):
        """Draw frame information overlay."""
        h, w = frame.shape[:2]
        
        info_text = [
            f"Frame: {frame_number}",
            f"Persons: {person_count}",
        ]
        
        y_offset = 30
        for text in info_text:
            self._draw_text(frame, text, (10, y_offset), self.colors["person_box"])
            y_offset += 30
    
    def _draw_alert(self, frame: np.ndarray, suspicion_score: int):
        """Draw alert overlay for suspicious behavior."""
        h, w = frame.shape[:2]
        
        # Draw alert banner
        alert_text = f"ALERT! Suspicion Score: {suspicion_score}"
        text_size = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)[0]
        
        # Background rectangle
        x_center = w // 2 - text_size[0] // 2
        y_pos = 60
        cv2.rectangle(
            frame,
            (x_center - 10, y_pos - 40),
            (x_center + text_size[0] + 10, y_pos + 10),
            self.colors["alert_box"],
            -1
        )
        
        # Text
        cv2.putText(
            frame,
            alert_text,
            (x_center, y_pos),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            self.colors["text_fg"],
            3
        )

    def _draw_status(self, frame: np.ndarray, is_suspicious: bool):
        """Draw explicit status badge: green NORMAL or red SUSPICIOUS."""
        status_text = "SUSPICIOUS" if is_suspicious else "NORMAL"
        badge_color = self.colors["alert_box"] if is_suspicious else self.colors["person_box"]
        self._draw_text(frame, f"Status: {status_text}", (10, 90), badge_color)
    
    def _draw_text(
        self,
        frame: np.ndarray,
        text: str,
        position: tuple,
        color: tuple,
        font_scale: float = 0.6,
        thickness: int = 2
    ):
        """Draw text with background for better visibility."""
        x, y = position
        
        # Get text size
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        
        # Draw background rectangle
        cv2.rectangle(
            frame,
            (x, y - text_size[1] - 5),
            (x + text_size[0] + 5, y + 5),
            self.colors["text_bg"],
            -1
        )
        
        # Draw text
        cv2.putText(
            frame,
            text,
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            color,
            thickness
        )
