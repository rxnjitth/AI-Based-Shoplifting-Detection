# ML Models

This directory contains the two pre-trained YOLOv8 models used by the Smart Theft Detection pipeline.

---

## Models

### 1. `yolov8m-pose.pt` — Person Detection + Pose Estimation
| Property | Value |
|---|---|
| **Size** | ~52 MB |
| **Architecture** | YOLOv8m-Pose (medium, keypoint head) |
| **Purpose** | Detects persons (class 0) AND estimates 17 COCO body keypoints per person |
| **Tracker** | ByteTrack (built-in via `model.track()`) |
| **Input** | 640 × 640 px |
| **Device** | CUDA (RTX 3050) / CPU fallback |

Used by: `backend/app/services/person_detector.py` and `pose_estimator.py`

### 2. `yolov8m.pt` — Product / Object Detection
| Property | Value |
|---|---|
| **Size** | ~52 MB |
| **Architecture** | YOLOv8m (medium, detection head) |
| **Purpose** | Detects retail products and objects near person's hands |
| **Classes** | 80 COCO classes |
| **Input** | 640 × 640 px |

Used by: `backend/app/services/product_detector.py`

---

## Auto-Download

Both models are downloaded automatically on first run if not present:

```python
from ultralytics import YOLO
YOLO("yolov8m-pose.pt")  # downloads ~52MB
YOLO("yolov8m.pt")       # downloads ~52MB
```

## Manual Download

```bash
# From Ultralytics GitHub releases
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m-pose.pt
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m.pt
```

---

## What Was Removed

| Removed | Reason |
|---|---|
| `yolov8n.pt` | Replaced by the more accurate `yolov8m-pose.pt` |
| `yolov8s.pt` | Duplicate, unused |
| `pose_landmarker_full.task` | MediaPipe replaced by YOLO keypoints (zero extra inference) |

> **Note:** MediaPipe is no longer used. Pose keypoints come directly from `yolov8m-pose.pt`'s keypoint head — no separate pose model needed.
