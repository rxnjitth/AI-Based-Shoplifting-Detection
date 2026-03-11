"""
Test suite for behavior analysis.
"""
import sys
from pathlib import Path
import pytest

# Add backend directory to path to resolve imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.behavior_analyzer import BehaviorAnalyzer, BehaviorFrame


def test_behavior_analyzer_initialization():
    """Test analyzer initialization."""
    analyzer = BehaviorAnalyzer()
    assert analyzer is not None
    assert analyzer.window_size == 30
    assert len(analyzer.suspicious_sequences) == 0


def test_analyze_frame():
    """Test frame analysis."""
    analyzer = BehaviorAnalyzer()
    
    # Mock data
    person = {"bbox": [100, 100, 200, 200], "confidence": 0.9}
    landmarks = {
        "left_hand": {"x": 150, "y": 120, "z": 0, "visibility": 1.0},
        "right_hand": {"x": 160, "y": 120, "z": 0, "visibility": 1.0},
        "left_shoulder": {"x": 140, "y": 100, "z": 0, "visibility": 1.0},
        "right_shoulder": {"x": 170, "y": 100, "z": 0, "visibility": 1.0},
        "waist": {"x": 155, "y": 150, "z": 0, "visibility": 1.0},
        "left_hip": {"x": 145, "y": 160, "z": 0, "visibility": 1.0},
        "right_hip": {"x": 165, "y": 160, "z": 0, "visibility": 1.0}
    }
    interaction = {
        "primary_zone": "neutral",
        "is_suspicious": False,
        "left_hand": {"zone": "neutral", "action": "idle", "position": landmarks["left_hand"]},
        "right_hand": {"zone": "neutral", "action": "idle", "position": landmarks["right_hand"]}
    }
    
    # Should not raise exception
    analyzer.analyze_frame(0, 0.0, person, landmarks, interaction)
    assert len(analyzer.frame_buffer) == 1


def test_generate_alerts():
    """Test alert generation."""
    analyzer = BehaviorAnalyzer()
    
    alerts = analyzer.generate_alerts()
    assert isinstance(alerts, list)


def test_reset():
    """Test analyzer reset."""
    analyzer = BehaviorAnalyzer()
    analyzer.reset()
    
    assert len(analyzer.frame_buffer) == 0
    assert len(analyzer.zone_history) == 0
    assert len(analyzer.suspicious_sequences) == 0


def _frame(frame_number: int, zone: str, left_zone: str, right_zone: str, left_action: str, right_action: str):
    return BehaviorFrame(
        frame_number=frame_number,
        timestamp=frame_number / 10.0,
        person_bbox=[100, 100, 200, 300],
        track_id=1,
        zone=zone,
        action=left_action,
        interaction={
            "left_hand": {"zone": left_zone, "action": left_action},
            "right_hand": {"zone": right_zone, "action": right_action},
        },
        landmarks={},
    )


def test_shelf_to_basket_is_not_flagged_as_theft():
    analyzer = BehaviorAnalyzer(window_size=5)

    frames = [
        _frame(1, "shelf", "shelf", "neutral", "reaching", "idle"),
        _frame(2, "shelf", "shelf", "neutral", "reaching", "idle"),
        _frame(3, "basket", "basket", "neutral", "placing", "idle"),
        _frame(4, "basket", "basket", "neutral", "placing", "idle"),
        _frame(5, "basket", "basket", "neutral", "placing", "idle"),
    ]

    score, reason, transitions = analyzer._calculate_suspicion_score(frames)
    assert score < analyzer.threshold
    assert "shelf->pocket" not in transitions
    assert "Shelf to basket/trolley movement (normal)" in reason


def test_shelf_to_pocket_stays_suspicious():
    analyzer = BehaviorAnalyzer(window_size=5)

    frames = [
        _frame(1, "shelf", "shelf", "neutral", "reaching", "idle"),
        _frame(2, "shelf", "shelf", "neutral", "reaching", "idle"),
        _frame(3, "pocket", "pocket", "neutral", "concealing", "idle"),
        _frame(4, "pocket", "pocket", "neutral", "concealing", "idle"),
        _frame(5, "pocket", "pocket", "neutral", "concealing", "idle"),
    ]

    score, _, transitions = analyzer._calculate_suspicion_score(frames)
    assert score >= analyzer.threshold
    assert "shelf->pocket" in transitions
