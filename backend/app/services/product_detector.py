"""
Product detection layer based on YOLO classes.
Detects likely retail items in scene.
"""
from typing import Dict, List, Optional
from ultralytics import YOLO
import torch

from app.config import settings

# Auto-detect best available device
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class ProductDetector:
    """Detects product-like objects while excluding persons."""

    PRODUCT_KEYWORDS = {
        "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl",
        "banana", "apple", "sandwich", "orange", "broccoli", "carrot",
        "hot dog", "pizza", "donut", "cake", "milk", "food"
    }

    def __init__(self, model: Optional[YOLO] = None):
        # Use the general COCO model for product class detection.
        # yolov8m-pose.pt (person_detector) is specialized for people — can't
        # detect product categories. yolov8m.pt handles all 80 COCO classes.
        self.model = model or YOLO(settings.yolo_product_model_path)
        self.confidence_threshold = settings.product_confidence_threshold
        self.iou_threshold = settings.yolo_iou_threshold
        self.input_size = settings.yolo_input_size

    def detect_products(self, frame) -> List[Dict]:
        results = self.model(
            frame,
            verbose=False,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            imgsz=self.input_size,
            half=False,
            device=DEVICE,
        )

        products: List[Dict] = []
        for result in results:
            boxes = result.boxes
            if len(boxes) == 0:
                continue
                
            names = result.names
            # Batch process boxes for better performance
            class_ids = boxes.cls.cpu().numpy()
            confidences = boxes.conf.cpu().numpy()
            bboxes = boxes.xyxy.cpu().numpy()

            for i in range(len(boxes)):
                class_id = int(class_ids[i])
                # Early exit optimizations
                if class_id == 0:  # Skip person class
                    continue
                    
                label = str(names.get(class_id, "")).lower()
                if label not in self.PRODUCT_KEYWORDS:
                    continue

                products.append({
                    "bbox": bboxes[i].tolist(),
                    "confidence": float(confidences[i]),
                    "class_id": class_id,
                    "label": label,
                })

        return products
