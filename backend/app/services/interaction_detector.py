"""
Human-Object Interaction Detection Module.
Implements Layer 4: Detects hand interactions with zones (shelf, pocket, bag, basket/trolley).
"""
from typing import Dict, Optional, List
import numpy as np


class InteractionDetector:
    """
    Detects interactions between hands and object zones.
    Uses heuristic-based zone detection.
    """
    
    def __init__(self):
        """Initialize interaction detector."""
        pass
    
    def detect_interaction(self, landmarks: Dict, person: Dict) -> Dict:
        """
        Detect hand interactions with different zones.
        
        Args:
            landmarks: Pose landmarks from PoseEstimator
            person: Person detection data
            
        Returns:
            Dictionary containing interaction information
        """
        # Check if landmarks has required keys
        if not landmarks or "left_hand" not in landmarks or "right_hand" not in landmarks:
            # Return default interaction if landmarks are incomplete
            return {
                "left_hand": {
                    "zone": "unknown",
                    "action": "idle",
                    "position": {}
                },
                "right_hand": {
                    "zone": "unknown",
                    "action": "idle",
                    "position": {}
                },
                "primary_zone": "neutral",
                "is_suspicious": False
            }
        
        # Detect zones for each hand
        left_hand_zone = self._detect_hand_zone(
            landmarks["left_hand"],
            landmarks,
            "left"
        )
        
        right_hand_zone = self._detect_hand_zone(
            landmarks["right_hand"],
            landmarks,
            "right"
        )
        
        # Detect movement patterns
        left_action = self._classify_action(landmarks, "left", left_hand_zone)
        right_action = self._classify_action(landmarks, "right", right_hand_zone)
        
        interaction = {
            "left_hand": {
                "zone": left_hand_zone,
                "action": left_action,
                "position": landmarks["left_hand"]
            },
            "right_hand": {
                "zone": right_hand_zone,
                "action": right_action,
                "position": landmarks["right_hand"]
            },
            "primary_zone": self._get_primary_zone(left_hand_zone, right_hand_zone),
            "is_suspicious": self._is_suspicious_interaction(
                left_hand_zone,
                right_hand_zone,
                left_action,
                right_action
            )
        }
        
        return interaction
    
    def _detect_hand_zone(self, hand: Dict, landmarks: Dict, side: str) -> str:
        """
        Detect which zone a hand is in based on position relative to body.
        Uses relative body proportions instead of fixed pixel distances so
        detection works regardless of camera distance or resolution.
        """
        if hand["visibility"] < 0.4:
            return "unknown"

        hand_y = hand["y"]
        hand_x = hand["x"]

        shoulder_y  = landmarks[f"{side}_shoulder"]["y"]
        waist_y     = landmarks["waist"]["y"]
        hip_y       = landmarks[f"{side}_hip"]["y"]
        shoulder_x  = landmarks[f"{side}_shoulder"]["x"]
        torso_center_x = (
            landmarks["left_shoulder"]["x"] + landmarks["right_shoulder"]["x"]
        ) / 2

        # Body height reference — distance from shoulder to hip
        body_height = max(1.0, abs(hip_y - shoulder_y))

        x_from_shoulder   = abs(hand_x - shoulder_x)
        x_from_center     = abs(hand_x - torso_center_x)

        # Normalised thresholds (fraction of body_height)
        # These stay consistent regardless of camera distance / resolution
        reach_threshold   = body_height * 0.35   # hand extended outward
        pocket_x_max      = body_height * 0.45   # close to body side
        center_x_max      = body_height * 0.70   # close to torso centre
        bag_x_min         = body_height * 0.60   # clearly away from centre
        basket_x_min      = body_height * 0.65   # further away, below hips

        # SHELF: hand above waist and reaching outward
        if hand_y < waist_y and x_from_shoulder > reach_threshold:
            return "shelf"

        # BASKET/TROLLEY: hand below hips and away from torso
        if hand_y >= (hip_y - body_height * 0.08) and x_from_center > basket_x_min:
            return "basket"

        # POCKET: hand between waist and lower hip, close to body
        if waist_y < hand_y < (hip_y + body_height * 0.55):
            if x_from_shoulder < pocket_x_max and x_from_center < center_x_max:
                return "pocket"

        # BAG: hand at torso level, clearly away from centre
        if shoulder_y < hand_y < hip_y and x_from_shoulder > bag_x_min:
            return "bag"

        return "neutral"
    
    def _classify_action(self, landmarks: Dict, side: str, zone: str) -> str:
        """
        Classify hand action based on position and context.
        
        Args:
            landmarks: Pose landmarks
            side: "left" or "right"
            
        Returns:
            Action classification: "reaching", "placing", "concealing", "idle"
        """
        hand = landmarks[f"{side}_hand"]
        elbow = landmarks[f"{side}_elbow"]
        shoulder = landmarks[f"{side}_shoulder"]
        waist = landmarks["waist"]
        
        if hand["visibility"] < 0.5:
            return "unknown"
        
        # Calculate arm extension
        hand_to_shoulder_dist = np.sqrt(
            (hand["x"] - shoulder["x"]) ** 2 +
            (hand["y"] - shoulder["y"]) ** 2
        )
        
        elbow_to_shoulder_dist = np.sqrt(
            (elbow["x"] - shoulder["x"]) ** 2 +
            (elbow["y"] - shoulder["y"]) ** 2
        )
        
        extension_ratio = hand_to_shoulder_dist / (elbow_to_shoulder_dist + 1e-6)

        # Body height for relative threshold
        body_height = max(1.0, abs(
            landmarks[f"{side}_hip"]["y"] - landmarks[f"{side}_shoulder"]["y"]
        ))

        # Zone-aware action classification keeps normal shopping behavior from
        # being mislabeled as concealment.
        if zone == "basket":
            return "placing"

        if extension_ratio > 1.3 and zone == "shelf":
            return "reaching"
        elif (extension_ratio < 0.9
              and zone == "pocket"
              and hand["y"] > waist["y"]
              and hand_to_shoulder_dist < body_height * 0.6):
            return "concealing"
        else:
            return "idle"
    
    def _get_primary_zone(self, left_zone: str, right_zone: str) -> str:
        """
        Determine primary active zone.
        
        Args:
            left_zone: Left hand zone
            right_zone: Right hand zone
            
        Returns:
            Primary zone
        """
        # Priority: shelf > pocket > basket > bag > neutral
        priority = ["shelf", "pocket", "basket", "bag", "neutral", "unknown"]
        
        for zone in priority:
            if left_zone == zone or right_zone == zone:
                return zone
        
        return "neutral"
    
    def _is_suspicious_interaction(
        self,
        left_zone: str,
        right_zone: str,
        left_action: str,
        right_action: str
    ) -> bool:
        """
        Determine if interaction pattern is suspicious.
        
        Args:
            left_zone, right_zone: Zone for each hand
            left_action, right_action: Action for each hand
            
        Returns:
            True if suspicious
        """
        # Suspicious patterns:
        # - Hand in pocket
        # - Concealing action
        # Shelf transitions are scored in BehaviorAnalyzer.
        
        suspicious_zones = ["pocket"]
        suspicious_actions = ["concealing"]
        
        if left_zone in suspicious_zones or right_zone in suspicious_zones:
            return True
        
        if left_action in suspicious_actions or right_action in suspicious_actions:
            return True
        
        return False
