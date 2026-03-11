# ML Models

This directory contains pre-trained machine learning models.

## YOLOv8n Model

The YOLOv8n model will be automatically downloaded on first run.

To manually download:
```bash
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
```

Or using Python:
```python
from ultralytics import YOLO
model = YOLO("yolov8n.pt")  # Will auto-download
```

## Model Information

- **YOLOv8n**: Nano version, optimized for speed
- **Size**: ~6MB
- **Classes**: 80 COCO classes (person is class 0)
- **Input**: 640x640 pixels

MediaPipe Pose is bundled with the mediapipe package and doesn't require separate model files.
