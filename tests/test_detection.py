"""
Test suite for person detection layer.
"""
import sys
from pathlib import Path
import pytest
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.person_detector import PersonDetector


def test_person_detector_initialization():
    """Test that detector initializes correctly."""
    detector = PersonDetector()
    assert detector is not None
    assert detector.model is not None
    assert detector.person_class_id == 0


def test_detect_persons_empty_frame():
    """Test detection on empty frame."""
    detector = PersonDetector()
    
    # Create blank frame
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    
    persons = detector.detect_persons(frame)
    assert isinstance(persons, list)


def test_bbox_string_conversion():
    """Test bounding box to string conversion."""
    detector = PersonDetector()
    
    bbox = [100, 200, 300, 400]
    bbox_str = detector.get_bbox_string(bbox)
    
    assert isinstance(bbox_str, str)
    assert '100' in bbox_str
    assert ',' in bbox_str
