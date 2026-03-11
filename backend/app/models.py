"""
Pydantic models for API request/response schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class AlertStatus(str, Enum):
    """Alert status enumeration."""
    NEW = "new"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"


class BehaviorLogSchema(BaseModel):
    """Schema for behavior log entries."""
    id: int
    frame_number: int
    left_hand_position: Optional[str] = None
    right_hand_position: Optional[str] = None
    action_type: Optional[str] = None
    confidence: Optional[float] = None
    zone: Optional[str] = None
    
    class Config:
        from_attributes = True


class EventSchema(BaseModel):
    """Schema for event timeline entries."""
    id: int
    event_type: str
    timestamp: datetime
    event_metadata: Optional[str] = None
    
    class Config:
        from_attributes = True


class AlertBase(BaseModel):
    """Base schema for alert data."""
    suspicion_score: float = Field(..., ge=0, le=100)
    reason: Optional[str] = None
    person_bbox: Optional[str] = None
    person_confidence: Optional[float] = None
    video_path: str
    snapshot_path: Optional[str] = None
    clip_path: Optional[str] = None
    frame_number: Optional[int] = None


class AlertCreate(AlertBase):
    """Schema for creating a new alert."""
    pass


class AlertUpdate(BaseModel):
    """Schema for updating an alert."""
    status: Optional[AlertStatus] = None
    reason: Optional[str] = None


class AlertResponse(AlertBase):
    """Schema for alert response."""
    id: int
    timestamp: datetime
    status: AlertStatus
    events: List[EventSchema] = []
    behavior_logs: List[BehaviorLogSchema] = []
    
    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """Schema for paginated alert list."""
    total: int
    alerts: List[AlertResponse]
    page: int
    page_size: int


class StatisticsResponse(BaseModel):
    """Schema for dashboard statistics."""
    total_alerts: int
    total_alerts_today: int
    average_suspicion_score: float
    alerts_by_status: dict
    alerts_by_hour: List[dict]
    peak_hour: Optional[int] = None


class VideoUploadResponse(BaseModel):
    """Schema for video upload response."""
    job_id: str
    filename: str
    file_path: str
    message: str


class HealthCheckResponse(BaseModel):
    """Schema for health check response."""
    status: str
    version: str
    timestamp: datetime
