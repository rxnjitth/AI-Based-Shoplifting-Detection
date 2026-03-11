"""
Pose Estimation Layer - MediaPipe Pose for skeletal tracking.
Implements Layer 3: Pose Estimation.
"""
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
from typing import Dict, Optional, List
import cv2
import os

from app.config import settings


class PoseEstimator:
    """
    Estimates human pose using MediaPipe Pose.
    Focuses on hand, elbow, and shoulder landmarks.
    """
    
    def __init__(self):
        """Initialize MediaPipe Pose Landmarker."""
        # Download model if not exists
        model_path = os.path.join(settings.models_dir, "pose_landmarker_full.task")
        if not os.path.exists(model_path):
            import urllib.request
            os.makedirs(settings.models_dir, exist_ok=True)
            print("📥 Downloading MediaPipe Pose model...")
            url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task"
            urllib.request.urlretrieve(url, model_path)
            print("✅ Model downloaded")
        
        # Create pose landmarker
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=settings.pose_detection_confidence,
            min_pose_presence_confidence=settings.pose_presence_confidence,
            min_tracking_confidence=settings.pose_tracking_confidence,
        )
        self.detector = vision.PoseLandmarker.create_from_options(options)
        
        # Landmark indices we care about (mediapipe pose has 33 landmarks)
        self.landmark_indices = {
            "left_shoulder": 11,
            "right_shoulder": 12,
            "left_elbow": 13,
            "right_elbow": 14,
            "left_wrist": 15,
            "right_wrist": 16,
            "left_hip": 23,
            "right_hip": 24,
        }
    
    def estimate_pose(self, frame: np.ndarray, person: Dict) -> Optional[Dict]:
        """
        Estimate pose for a detected person.
        
        Args:
            frame: Full frame image
            person: Person detection dict with bbox
            
        Returns:
            Dictionary of normalized landmarks or None if detection failed
        """
        # Extract person region from frame
        bbox = person["bbox"]
        x1, y1, x2, y2 = [int(coord) for coord in bbox]
        
        # Expand bbox slightly; full-body context improves landmark quality.
        pad_ratio = settings.pose_bbox_padding_ratio
        box_w = max(1, x2 - x1)
        box_h = max(1, y2 - y1)
        x_pad = int(box_w * pad_ratio)
        y_pad = int(box_h * pad_ratio)
        x1, y1, x2, y2 = x1 - x_pad, y1 - y_pad, x2 + x_pad, y2 + y_pad

        # Ensure bbox is within frame bounds
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        if x2 <= x1 or y2 <= y1:
            return None
        
        person_img = frame[y1:y2, x1:x2]
        
        # Convert BGR to RGB for MediaPipe
        person_rgb = cv2.cvtColor(person_img, cv2.COLOR_BGR2RGB)
        
        # Create MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=person_rgb)
        
        # Process with MediaPipe
        results = self.detector.detect(mp_image)
        
        if not results.pose_landmarks or len(results.pose_landmarks) == 0:
            return None
        
        # Extract key landmarks from first detected pose
        landmarks = self._extract_key_landmarks(
            results.pose_landmarks[0],
            person_img.shape,
            (x1, y1)  # Offset to convert back to full frame coordinates
        )
        
        return landmarks
    
    def _extract_key_landmarks(
        self,
        pose_landmarks,
        person_shape: tuple,
        offset: tuple
    ) -> Dict:
        """
        Extract and normalize key landmarks.
        
        Args:
            pose_landmarks: MediaPipe pose landmarks (list of NormalizedLandmark)
            person_shape: Shape of person crop (height, width, channels)
            offset: Offset (x, y) to convert to full frame coordinates
            
        Returns:
            Dictionary of landmark positions
        """
        h, w = person_shape[:2]
        offset_x, offset_y = offset
        
        landmarks = {}
        
        for name, landmark_id in self.landmark_indices.items():
            lm = pose_landmarks[landmark_id]
            
            # Convert normalized coordinates to pixel coordinates
            x_pixel = lm.x * w + offset_x
            y_pixel = lm.y * h + offset_y
            
            landmarks[name] = {
                "x": float(x_pixel),
                "y": float(y_pixel),
                "z": float(lm.z),  # Depth (relative to hips)
                "visibility": float(lm.visibility)
            }
        
        # Calculate derived positions
        landmarks["left_hand"] = landmarks["left_wrist"]
        landmarks["right_hand"] = landmarks["right_wrist"]
        
        # Calculate waist position (midpoint between hips)
        landmarks["waist"] = {
            "x": (landmarks["left_hip"]["x"] + landmarks["right_hip"]["x"]) / 2,
            "y": (landmarks["left_hip"]["y"] + landmarks["right_hip"]["y"]) / 2,
            "z": (landmarks["left_hip"]["z"] + landmarks["right_hip"]["z"]) / 2,
            "visibility": min(landmarks["left_hip"]["visibility"], landmarks["right_hip"]["visibility"])
        }
        
        return landmarks
    
    def get_hand_position_string(self, hand_landmark: Dict) -> str:
        """
        Convert hand landmark to string for database storage.
        
        Args:
            hand_landmark: Hand landmark dict with x, y
            
        Returns:
            String representation "x,y"
        """
        return f"{hand_landmark['x']:.2f},{hand_landmark['y']:.2f}"
    
    def __del__(self):
        """Cleanup MediaPipe resources."""
        if hasattr(self, 'pose'):
            self.pose.close()
