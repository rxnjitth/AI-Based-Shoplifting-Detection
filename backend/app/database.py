"""
Database models and session management using SQLAlchemy.
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum

from app.config import settings

# Create database engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class AlertStatus(str, enum.Enum):
    """Alert status enumeration."""
    NEW = "new"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"


class Alert(Base):
    """Alert model representing a suspicious behavior detection."""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    suspicion_score = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    
    # Person detection info
    person_bbox = Column(String(100), nullable=True)  # Stored as "x1,y1,x2,y2"
    person_confidence = Column(Float, nullable=True)
    
    # Video and evidence paths
    video_path = Column(String(500), nullable=False)
    snapshot_path = Column(String(500), nullable=True)
    clip_path = Column(String(500), nullable=True)
    
    # Alert status
    status = Column(Enum(AlertStatus), default=AlertStatus.NEW, nullable=False)
    
    # Frame information
    frame_number = Column(Integer, nullable=True)
    
    # Relationships
    events = relationship("Event", back_populates="alert", cascade="all, delete-orphan")
    behavior_logs = relationship("BehaviorLog", back_populates="alert", cascade="all, delete-orphan")


class Event(Base):
    """Event model for timeline tracking."""
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # e.g., "hand_near_shelf", "hand_to_pocket"
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    event_metadata = Column(Text, nullable=True)  # JSON string for additional data
    
    # Relationship
    alert = relationship("Alert", back_populates="events")


class BehaviorLog(Base):
    """Behavior log for detailed frame-by-frame analysis."""
    __tablename__ = "behavior_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    frame_number = Column(Integer, nullable=False)
    
    # Hand positions (stored as "x,y" strings)
    left_hand_position = Column(String(50), nullable=True)
    right_hand_position = Column(String(50), nullable=True)
    
    # Action classification
    action_type = Column(String(50), nullable=True)  # e.g., "reaching", "grabbing", "concealing"
    confidence = Column(Float, nullable=True)
    
    # Zone information
    zone = Column(String(50), nullable=True)  # e.g., "shelf", "pocket", "bag"
    
    # Relationship
    alert = relationship("Alert", back_populates="behavior_logs")


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Dependency function to get database session.
    Use with FastAPI's Depends.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
