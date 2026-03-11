"""
Behavior Analysis Engine - Implements suspicion scoring and pattern detection.
Implements Layer 5: Suspicious Behavior Detection Engine.
"""
from typing import Dict, List, Optional
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

from app.config import settings


@dataclass
class BehaviorFrame:
    """Represents behavior data for a single frame."""
    frame_number: int
    timestamp: float
    person_bbox: list
    track_id: Optional[int]
    zone: str
    action: str
    interaction: Dict
    landmarks: Dict


@dataclass
class SuspiciousSequence:
    """Represents a sequence of suspicious behavior."""
    start_frame: int
    end_frame: int
    start_timestamp: float
    end_timestamp: float
    peak_frame: int
    peak_timestamp: float
    suspicion_score: float
    reason: str
    person_bbox: list
    track_id: Optional[int]
    zone_transitions: List[str] = field(default_factory=list)
    frames: List[BehaviorFrame] = field(default_factory=list)


class BehaviorAnalyzer:
    """
    Analyzes behavior patterns and calculates suspicion scores.
    Uses sliding window approach to detect suspicious sequences.
    """
    
    def __init__(self, window_size: int = 30):
        """
        Initialize behavior analyzer.
        
        Args:
            window_size: Number of frames to analyze in sliding window (default 30 = 3 seconds at 10 fps)
        """
        self.window_size = window_size
        self.frame_buffer = deque(maxlen=window_size)
        # Reduced zone history for memory efficiency
        self.zone_history = deque(maxlen=50)  # Track zone transitions
        self.suspicious_sequences: List[SuspiciousSequence] = []
        self.current_sequence: Optional[BehaviorFrame] = None
        
        # Cache scoring weights from config (avoid repeated attribute access)
        self.score_base = settings.score_base_shelf_pickup
        self.score_shelf_to_pocket = settings.score_shelf_to_pocket
        self.score_shelf_to_bag = settings.score_shelf_to_bag
        self.score_repeated_touch = settings.score_repeated_touch
        self.score_abnormal_motion = settings.score_abnormal_motion
        
        self.threshold = settings.suspicion_score_threshold
    
    def analyze_frame(
        self,
        frame_number: int,
        timestamp: float,
        person: Dict,
        landmarks: Dict,
        interaction: Dict
    ):
        """
        Analyze a single frame and update behavior state.
        
        Args:
            frame_number: Current frame number
            timestamp: Timestamp in seconds
            person: Person detection data
            landmarks: Pose landmarks
            interaction: Interaction detection data
        """
        # Create behavior frame
        behavior_frame = BehaviorFrame(
            frame_number=frame_number,
            timestamp=timestamp,
            person_bbox=person["bbox"],
            track_id=person.get("track_id"),
            zone=interaction["primary_zone"],
            action=interaction["left_hand"]["action"],  # Use primary hand
            interaction=interaction,
            landmarks=landmarks
        )
        
        # Add to buffer
        self.frame_buffer.append(behavior_frame)
        self.zone_history.append(interaction["primary_zone"])
        
        # Analyze window
        if len(self.frame_buffer) >= self.window_size:
            self._analyze_window()
    
    def _analyze_window(self):
        """Analyze current window for suspicious patterns."""
        frames = list(self.frame_buffer)
        
        # Calculate suspicion score for this window
        score, reason, transitions = self._calculate_suspicion_score(frames)
        
        # If score exceeds threshold, create or update sequence
        if score >= self.threshold:
            peak_frame = frames[len(frames) // 2]  # Middle frame as peak
            
            if self.current_sequence is None:
                # Start new sequence
                self.current_sequence = SuspiciousSequence(
                    start_frame=frames[0].frame_number,
                    end_frame=frames[-1].frame_number,
                    start_timestamp=frames[0].timestamp,
                    end_timestamp=frames[-1].timestamp,
                    peak_frame=peak_frame.frame_number,
                    peak_timestamp=peak_frame.timestamp,
                    suspicion_score=score,
                    reason=reason,
                    person_bbox=peak_frame.person_bbox,
                    track_id=peak_frame.track_id,
                    zone_transitions=transitions,
                    frames=frames.copy()
                )
            else:
                # Update existing sequence
                self.current_sequence.end_frame = frames[-1].frame_number
                self.current_sequence.end_timestamp = frames[-1].timestamp
                if score > self.current_sequence.suspicion_score:
                    self.current_sequence.suspicion_score = score
                    self.current_sequence.peak_frame = peak_frame.frame_number
                    self.current_sequence.peak_timestamp = peak_frame.timestamp
                    self.current_sequence.person_bbox = peak_frame.person_bbox
                    self.current_sequence.track_id = peak_frame.track_id
                self.current_sequence.frames.extend(frames)
        else:
            # End current sequence if it exists
            if self.current_sequence is not None:
                self.suspicious_sequences.append(self.current_sequence)
                self.current_sequence = None
    
    def _calculate_suspicion_score(self, frames: List[BehaviorFrame]) -> tuple:
        """
        Calculate suspicion score for a sequence of frames.
        
        Args:
            frames: List of behavior frames
            
        Returns:
            Tuple of (score, reason, zone_transitions)
        """
        score = 0
        reasons = []
        zone_transitions = []
        
        # Extract zones from frames
        zones = [f.zone for f in frames]
        
        # Check for shelf interaction
        has_shelf = "shelf" in zones
        has_pocket = "pocket" in zones
        has_bag = "bag" in zones
        has_basket = "basket" in zones
        
        # Base score for shelf interaction
        if has_shelf:
            score += self.score_base
            reasons.append("Hand near shelf")
        
        # Critical transitions
        if has_shelf and has_pocket:
            score += self.score_shelf_to_pocket
            reasons.append("Shelf to pocket movement")
            zone_transitions.append("shelf->pocket")
        
        if has_shelf and has_bag and not has_basket:
            score += self.score_shelf_to_bag
            reasons.append("Shelf to bag movement")
            zone_transitions.append("shelf->bag")

        if has_shelf and has_basket:
            reasons.append("Shelf to basket/trolley movement (normal)")
        
        # Repeated touches (shelf appears multiple times)
        shelf_count = zones.count("shelf")
        if shelf_count > len(zones) * 0.5:
            score += self.score_repeated_touch
            reasons.append("Repeated shelf contact")
        
        # Count concealment only when hand is actually near pocket zone.
        concealing_actions = 0
        for f in frames:
            left = f.interaction["left_hand"]
            right = f.interaction["right_hand"]
            if left["action"] == "concealing" and left["zone"] == "pocket":
                concealing_actions += 1
            if right["action"] == "concealing" and right["zone"] == "pocket":
                concealing_actions += 1
        
        if concealing_actions > 0:
            score += self.score_abnormal_motion
            reasons.append("Concealing hand motion")
        
        # Duration multiplier (longer suspicious behavior = higher score)
        if len(frames) > self.window_size * 0.8:
            score *= 1.1
            reasons.append("Prolonged suspicious activity")
        
        reason_text = "; ".join(reasons) if reasons else "Unknown suspicious behavior"
        
        return score, reason_text, zone_transitions
    
    def generate_alerts(self) -> List[Dict]:
        """
        Generate alerts from detected suspicious sequences.
        
        Returns:
            List of alert data dictionaries
        """
        # Finalize any ongoing sequence
        if self.current_sequence is not None:
            self.suspicious_sequences.append(self.current_sequence)
            self.current_sequence = None
        
        # Convert sequences to alert data
        alerts = []
        
        for sequence in self.suspicious_sequences:
            alert_data = {
                "frame_number": sequence.peak_frame,
                "timestamp": sequence.peak_timestamp,
                "suspicion_score": min(100, sequence.suspicion_score),  # Cap at 100
                "reason": sequence.reason,
                "person_bbox": sequence.person_bbox,
                "track_id": sequence.track_id,
                "zone_transitions": sequence.zone_transitions,
                "start_frame": sequence.start_frame,
                "end_frame": sequence.end_frame,
                "duration": sequence.end_timestamp - sequence.start_timestamp
            }
            alerts.append(alert_data)
        
        return alerts
    
    def reset(self):
        """Reset analyzer state."""
        self.frame_buffer.clear()
        self.zone_history.clear()
        self.suspicious_sequences.clear()
        self.current_sequence = None
    
    def get_current_suspicion_score(self) -> int:
        """
        Get the current suspicion score based on the sliding window.
        
        Returns:
            Current suspicion score (0-100)
        """
        if len(self.frame_buffer) < self.window_size // 2:
            return 0
        
        frames = list(self.frame_buffer)
        score, _, _ = self._calculate_suspicion_score(frames)
        return min(100, int(score))
