"""
Alert management API endpoints.
Handles CRUD operations for alerts.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import os

from app.database import get_db, Alert, AlertStatus
from app.models import AlertResponse, AlertListResponse, AlertUpdate
from app.config import settings

router = APIRouter()


def normalize_path(path: Optional[str], evidence_dir: str) -> Optional[str]:
    """Normalize evidence paths to filename only when backing file exists."""
    if not path:
        return None
    filename = os.path.basename(path)
    full_path = os.path.join(evidence_dir, filename)
    if not os.path.exists(full_path):
        return None
    return filename


@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[AlertStatus] = Query(None, description="Filter by status"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum suspicion score"),
    from_date: Optional[datetime] = Query(None, description="Filter from date"),
    to_date: Optional[datetime] = Query(None, description="Filter to date"),
    db: Session = Depends(get_db)
):
    """
    List all alerts with optional filtering and pagination.
    """
    query = db.query(Alert)
    
    # Apply filters
    if status:
        query = query.filter(Alert.status == status)
    if min_score is not None:
        query = query.filter(Alert.suspicion_score >= min_score)
    if from_date:
        query = query.filter(Alert.timestamp >= from_date)
    if to_date:
        query = query.filter(Alert.timestamp <= to_date)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    alerts = query.order_by(Alert.timestamp.desc()).offset(offset).limit(page_size).all()
    
    # Normalize paths
    for alert in alerts:
        alert.snapshot_path = normalize_path(alert.snapshot_path, settings.evidence_snapshots_dir)
        alert.clip_path = normalize_path(alert.clip_path, settings.evidence_clips_dir)
    
    return AlertListResponse(
        total=total,
        alerts=alerts,
        page=page,
        page_size=page_size
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific alert.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    
    # Normalize paths
    alert.snapshot_path = normalize_path(alert.snapshot_path, settings.evidence_snapshots_dir)
    alert.clip_path = normalize_path(alert.clip_path, settings.evidence_clips_dir)
    
    return alert


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    update_data: AlertUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an alert (typically to change status or add notes).
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    
    # Update fields
    if update_data.status is not None:
        alert.status = update_data.status
    if update_data.reason is not None:
        alert.reason = update_data.reason
    
    db.commit()
    db.refresh(alert)
    
    return alert


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    """
    Delete an alert and its associated data.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    
    db.delete(alert)
    db.commit()
    
    return {"message": f"Alert {alert_id} deleted successfully"}
