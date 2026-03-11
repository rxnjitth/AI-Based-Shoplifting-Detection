"""
Live detection API endpoints for real-time camera feeds.
Processes individual frames for immediate object detection.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List
import cv2
import numpy as np
import base64

from app.services.person_detector import PersonDetector
from app.services.product_detector import ProductDetector
from app.services.pose_estimator import PoseEstimator
from app.services.interaction_detector import InteractionDetector

router = APIRouter()

# Initialize detectors (singleton for performance)
person_detector = PersonDetector()
product_detector = ProductDetector(model=person_detector.model)  # Reuse YOLO model
pose_estimator = PoseEstimator()
interaction_detector = InteractionDetector()


class DetectionRequest(BaseModel):
    image: str  # Base64 encoded image


@router.post("/detect-frame-base64")
async def detect_frame_base64(data: DetectionRequest):
    """
    Detect objects in a base64-encoded frame from live camera feed.
    Optimized for browser-based camera streams.
    
    Args:
        data: JSON with "image" key containing base64-encoded image
        
    Returns:
        Detection results
    """
    try:
        # Decode base64 image
        image_data = data.image
        
        # Remove data URL prefix if present
        if "," in image_data:
            image_data = image_data.split(",")[1]
        
        img_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            raise HTTPException(status_code=400, detail="Invalid image data")
        
        # Perform detections (lightweight processing)
        persons = person_detector.detect_persons(frame)
        products = product_detector.detect_products(frame)
        
        # Process each detected person
        detections = []
        for person in persons:
            bbox = person["bbox"]
            x1, y1, x2, y2 = map(int, bbox)
            
            # Validate bbox
            if x2 <= x1 or y2 <= y1:
                continue
                
            person_crop = frame[max(0, y1):min(frame.shape[0], y2), 
                              max(0, x1):min(frame.shape[1], x2)]
            
            landmarks = {}
            pose_detected = False
            if person_crop.size > 0:
                landmarks = pose_estimator.estimate_pose(person_crop, bbox)
                pose_detected = bool(landmarks and "left_hand" in landmarks)
            
            # Detect interactions only if pose was detected
            zone = "neutral"
            left_action = "idle"
            right_action = "idle"
            is_suspicious = False
            
            if pose_detected:
                try:
                    interaction = interaction_detector.detect_interaction(
                        landmarks=landmarks,
                        person=person
                    )
                    
                    # Extract interaction data safely
                    zone = interaction.get("primary_zone", "neutral")
                    left_action = interaction.get("left_hand", {}).get("action", "idle")
                    right_action = interaction.get("right_hand", {}).get("action", "idle")
                    
                    # Simple suspicion flag
                    is_suspicious = (
                        zone in ["shelf", "pocket", "bag"] and
                        (left_action in ["reaching", "grabbing"] or right_action in ["reaching", "grabbing"])
                    )
                except Exception as e:
                    # If interaction detection fails, use defaults
                    print(f"Interaction detection error: {e}")
                    pass
            
            detections.append({
                "person": {
                    "bbox": bbox,
                    "confidence": round(person["confidence"], 2)
                },
                "pose": {
                    "detected": pose_detected,
                    "landmarks_count": len(landmarks.get("landmarks", [])) if landmarks else 0
                },
                "interaction": {
                    "zone": zone,
                    "left_hand_action": left_action,
                    "right_hand_action": right_action,
                    "nearby_products": len(products)
                },
                "suspicious": is_suspicious
            })
        
        return {
            "success": True,
            "detections": detections,
            "person_count": len(persons),
            "product_count": len(products),
            "frame_processed": True,
            "has_suspicious_activity": any(d.get("suspicious", False) for d in detections)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")
