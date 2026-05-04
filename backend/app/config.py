"""
Configuration management for the Smart Theft Detection System.
Loads settings from environment variables with defaults.
"""
from pydantic_settings import BaseSettings
from typing import List
import os
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "sqlite:///./theft_detection.db"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    
    # File Storage
    upload_dir: str = "../data/uploads"
    evidence_snapshots_dir: str = "../data/evidence/snapshots"
    evidence_clips_dir: str = "../data/evidence/clips"
    
    # ML Models
    models_dir: str = "../ml_models"
    yolo_model_path: str = "../ml_models/yolov8n.pt"
    
    # Detection Settings (Optimized for speed)
    person_confidence_threshold: float = 0.5
    product_confidence_threshold: float = 0.4  # Increased for fewer false positives
    yolo_iou_threshold: float = 0.5  # Increased for better NMS efficiency
    yolo_input_size: int = 640  # Reduced from 960 for 2x faster inference
    video_processing_fps: int = 10
    pose_estimation_interval: int = 3  # Increased from 2 for better performance
    pose_detection_confidence: float = 0.6
    pose_presence_confidence: float = 0.6
    pose_tracking_confidence: float = 0.6
    pose_bbox_padding_ratio: float = 0.15
    suspicion_score_threshold: int = 70
    
    # Behavior Scoring Weights
    score_base_shelf_pickup: int = 30
    score_shelf_to_pocket: int = 40
    score_shelf_to_bag: int = 20
    score_repeated_touch: int = 10
    score_abnormal_motion: int = 10
    
    # Evidence Settings
    clip_duration_before: int = 5
    clip_duration_after: int = 5

    # EZVIZ / RTSP Camera defaults (override per-request or via env)
    ezviz_camera_id: str = "ezviz-1"
    ezviz_rtsp_url: str = ""
    ezviz_default_port: int = 554
    ezviz_default_channel: int = 1
    ezviz_default_stream: str = "main"
    
    class Config:
        # Support running from either project root or backend directory.
        env_file = (str(ROOT_DIR / ".env"), str(BACKEND_DIR / ".env"))
        case_sensitive = False

    def model_post_init(self, __context) -> None:
        """Normalize relative paths against backend directory for stable runtime behavior."""
        self.upload_dir = self._resolve_backend_path(self.upload_dir)
        self.evidence_snapshots_dir = self._resolve_backend_path(self.evidence_snapshots_dir)
        self.evidence_clips_dir = self._resolve_backend_path(self.evidence_clips_dir)
        self.models_dir = self._resolve_backend_path(self.models_dir)
        self.yolo_model_path = self._resolve_backend_path(self.yolo_model_path)

    @staticmethod
    def _resolve_backend_path(path_value: str) -> str:
        path = Path(path_value)
        if path.is_absolute():
            return str(path)
        return str((BACKEND_DIR / path).resolve())
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist."""
        directories = [
            self.upload_dir,
            self.evidence_snapshots_dir,
            self.evidence_clips_dir,
            self.models_dir,
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)


# Global settings instance
settings = Settings()
