"""
Statistics API endpoints for dashboard analytics.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional

from app.database import get_db, Alert, AlertStatus
from app.models import StatisticsResponse

router = APIRouter()


@router.get("/", response_model=StatisticsResponse)
async def get_statistics(
    from_date: Optional[datetime] = Query(None, description="Start date for statistics"),
    to_date: Optional[datetime] = Query(None, description="End date for statistics"),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics and analytics.
    """
    # Default to last 30 days if no date range specified
    if not from_date:
        from_date = datetime.utcnow() - timedelta(days=30)
    if not to_date:
        to_date = datetime.utcnow()
    
    # Total alerts in date range
    total_alerts = db.query(Alert).filter(
        Alert.timestamp >= from_date,
        Alert.timestamp <= to_date
    ).count()
    
    # Total alerts today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total_alerts_today = db.query(Alert).filter(
        Alert.timestamp >= today_start
    ).count()
    
    # Average suspicion score
    avg_score_result = db.query(func.avg(Alert.suspicion_score)).filter(
        Alert.timestamp >= from_date,
        Alert.timestamp <= to_date
    ).scalar()
    average_suspicion_score = round(float(avg_score_result), 2) if avg_score_result else 0.0
    
    # Alerts by status
    status_counts = db.query(
        Alert.status,
        func.count(Alert.id)
    ).filter(
        Alert.timestamp >= from_date,
        Alert.timestamp <= to_date
    ).group_by(Alert.status).all()
    
    alerts_by_status = {
        status.value: count for status, count in status_counts
    }
    # Ensure all statuses are present
    for status in AlertStatus:
        if status.value not in alerts_by_status:
            alerts_by_status[status.value] = 0
    
    # Alerts by hour of day
    hour_counts = db.query(
        func.extract('hour', Alert.timestamp).label('hour'),
        func.count(Alert.id).label('count')
    ).filter(
        Alert.timestamp >= from_date,
        Alert.timestamp <= to_date
    ).group_by('hour').all()
    
    alerts_by_hour = [
        {"hour": int(hour), "count": count}
        for hour, count in hour_counts
    ]
    
    # Find peak hour
    peak_hour = max(alerts_by_hour, key=lambda x: x['count'])['hour'] if alerts_by_hour else None
    
    return StatisticsResponse(
        total_alerts=total_alerts,
        total_alerts_today=total_alerts_today,
        average_suspicion_score=average_suspicion_score,
        alerts_by_status=alerts_by_status,
        alerts_by_hour=alerts_by_hour,
        peak_hour=peak_hour
    )
