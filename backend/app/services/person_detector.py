"""
Person Detection Layer - YOLOv8-based person detection.
Implements Layer 2: Person Detection.
"""
from ultralytics import YOLO
import numpy as np
from typing import List, Dict, Optional
import os

from app.config import settings


class PersonDetector:
    """
    Detects persons in video frames using YOLOv8.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize person detector with YOLO model.
        
        Args:
            model_path: Path to YOLO model file. Defaults to config setting.
        """
        self.model_path = model_path or settings.yolo_model_path
        self.confidence_threshold = settings.person_confidence_threshold
        self.iou_threshold = settings.yolo_iou_threshold
        self.input_size = settings.yolo_input_size
        
        # Load YOLO model
        if os.path.exists(self.model_path):
            self.model = YOLO(self.model_path)
            print(f"✅ Loaded YOLO model from {self.model_path}")
        else:
            # Download YOLOv8n if not exists
            print(f"⏬ Downloading YOLOv8n model...")
            self.model = YOLO("yolov8n.pt")
            # Save to models directory
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            print(f"✅ YOLO model ready")
        
        # Person class ID in COCO dataset
        self.person_class_id = 0
    
    def detect_persons(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect persons in a frame.
        
        Args:
            frame: Input frame (BGR format from OpenCV)
            
        Returns:
            List of detected persons with bounding boxes and confidence scores
        """
        # Run inference with optimizations
        results = self.model(
            frame,
            verbose=False,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            imgsz=self.input_size,
            classes=[self.person_class_id],
            half=False,  # Disable FP16 for CPU stability
            device='cpu'  # Explicit device
        )
        
        persons = []
        
        # Process results with batched operations
        for result in results:
            boxes = result.boxes
            if len(boxes) == 0:
                continue
                
            # Batch convert to numpy for efficiency
            class_ids = boxes.cls.cpu().numpy()
            confidences = boxes.conf.cpu().numpy()
            bboxes = boxes.xyxy.cpu().numpy()
            
            for i in range(len(boxes)):
                # Filter for person class only
                class_id = int(class_ids[i])
                
                if class_id != self.person_class_id:
                    continue
                
                bbox = bboxes[i]
                confidence = float(confidences[i])
                
                person = {
                    "bbox": bbox.tolist(),
                    "confidence": confidence,
                    "class_id": class_id,
                    "center": self._get_bbox_center(bbox)
                }
                
                persons.append(person)
        
        return persons
    
    def _get_bbox_center(self, bbox: np.ndarray) -> tuple:
        """
        Calculate center point of bounding box.
        
        Args:
            bbox: Bounding box [x1, y1, x2, y2]
            
        Returns:
            Tuple of (center_x, center_y)
        """
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        return (float(center_x), float(center_y))
    
    def get_bbox_string(self, bbox: list) -> str:
        """
        Convert bounding box to string format for database storage.
        
        Args:
            bbox: Bounding box [x1, y1, x2, y2]
            
        Returns:
            String representation
        """
        return ",".join([f"{coord:.2f}" for coord in bbox])
