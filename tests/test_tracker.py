"""Unit tests for person tracker ID consistency."""

from app.services.person_tracker import PersonTracker


def _det(bbox, conf=0.9):
    x1, y1, x2, y2 = bbox
    return {
        "bbox": [x1, y1, x2, y2],
        "confidence": conf,
        "center": [((x1 + x2) / 2), ((y1 + y2) / 2)],
    }


def test_tracker_keeps_same_id_for_same_person():
    tracker = PersonTracker(iou_threshold=0.2, max_age=5)

    frame1 = tracker.update([_det([10, 10, 50, 80])])
    frame2 = tracker.update([_det([12, 12, 52, 82])])

    assert frame1[0]["track_id"] == frame2[0]["track_id"]


def test_tracker_assigns_new_id_for_new_person():
    tracker = PersonTracker(iou_threshold=0.2, max_age=5)

    frame1 = tracker.update([_det([10, 10, 50, 80])])
    frame2 = tracker.update([_det([10, 10, 50, 80]), _det([200, 20, 260, 100])])

    ids = {det["track_id"] for det in frame2}
    assert frame1[0]["track_id"] in ids
    assert len(ids) == 2


def test_tracker_expires_old_track():
    tracker = PersonTracker(iou_threshold=0.2, max_age=1)

    first = tracker.update([_det([10, 10, 50, 80])])[0]["track_id"]
    tracker.update([])
    tracker.update([])
    second = tracker.update([_det([10, 10, 50, 80])])[0]["track_id"]

    assert first != second
