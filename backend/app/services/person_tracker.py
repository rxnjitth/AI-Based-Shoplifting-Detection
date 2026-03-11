"""
Lightweight person tracking across frames.
Assigns stable track IDs to detections using IoU + center-distance matching.
"""
from typing import Dict, List


class PersonTracker:
    """IoU + center-distance tracker for assigning stable IDs per person."""

    def __init__(self, iou_threshold: float = 0.3, max_age: int = 20, max_center_distance: float = 80.0):
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.max_center_distance = max_center_distance
        self.next_track_id = 1
        self.tracks: Dict[int, Dict] = {}

    def update(self, detections: List[Dict]) -> List[Dict]:
        """Assign track IDs to current detections and update tracker state."""
        tracked_detections = [dict(det) for det in detections]

        # Age tracks first; matched tracks are reset to age 0 below.
        for track in self.tracks.values():
            track["age"] += 1

        matched_detection_indices = set()
        matched_track_ids = set()

        # Pass 1: Greedy IoU matching between existing tracks and new detections.
        for track_id, track_data in list(self.tracks.items()):
            best_idx = -1
            best_iou = 0.0

            for idx, det in enumerate(tracked_detections):
                if idx in matched_detection_indices:
                    continue

                iou = self._iou(track_data["bbox"], det["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_idx = idx

            if best_idx >= 0 and best_iou >= self.iou_threshold:
                det = tracked_detections[best_idx]
                self._assign_track(track_id, track_data, det)
                matched_detection_indices.add(best_idx)
                matched_track_ids.add(track_id)

        # Pass 2: center-distance fallback for unmatched tracks/detections.
        for track_id, track_data in list(self.tracks.items()):
            if track_id in matched_track_ids:
                continue

            best_idx = -1
            best_dist = float("inf")

            for idx, det in enumerate(tracked_detections):
                if idx in matched_detection_indices:
                    continue

                dist = self._center_distance(track_data["bbox"], det["bbox"])
                if dist < best_dist:
                    best_dist = dist
                    best_idx = idx

            if best_idx >= 0 and best_dist <= self.max_center_distance:
                det = tracked_detections[best_idx]
                self._assign_track(track_id, track_data, det)
                matched_detection_indices.add(best_idx)
                matched_track_ids.add(track_id)

        # Unmatched detections become new tracks.
        for idx, det in enumerate(tracked_detections):
            if idx in matched_detection_indices:
                continue

            track_id = self.next_track_id
            self.next_track_id += 1

            det["track_id"] = track_id
            self.tracks[track_id] = {
                "bbox": det["bbox"],
                "center": det.get("center"),
                "age": 0,
            }

        # Remove stale tracks.
        stale_ids = [track_id for track_id, track in self.tracks.items() if track["age"] > self.max_age]
        for track_id in stale_ids:
            del self.tracks[track_id]

        return tracked_detections

    @staticmethod
    def _assign_track(track_id: int, track_data: Dict, det: Dict) -> None:
        det["track_id"] = track_id
        track_data["bbox"] = det["bbox"]
        track_data["center"] = det.get("center")
        track_data["age"] = 0

    @staticmethod
    def _center_distance(box_a: List[float], box_b: List[float]) -> float:
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        acx = (ax1 + ax2) / 2.0
        acy = (ay1 + ay2) / 2.0
        bcx = (bx1 + bx2) / 2.0
        bcy = (by1 + by2) / 2.0

        dx = acx - bcx
        dy = acy - bcy
        return (dx * dx + dy * dy) ** 0.5

    @staticmethod
    def _iou(box_a: List[float], box_b: List[float]) -> float:
        """Compute IoU between two [x1, y1, x2, y2] boxes."""
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)

        inter_w = max(0.0, inter_x2 - inter_x1)
        inter_h = max(0.0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h

        area_a = max(0.0, (ax2 - ax1)) * max(0.0, (ay2 - ay1))
        area_b = max(0.0, (bx2 - bx1)) * max(0.0, (by2 - by1))

        union_area = area_a + area_b - inter_area
        if union_area <= 0:
            return 0.0

        return inter_area / union_area
