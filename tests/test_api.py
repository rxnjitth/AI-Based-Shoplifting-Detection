"""
Test suite for API endpoints.
"""
import pytest
import sys
import os
from pathlib import Path
from fastapi.testclient import TestClient

# Add backend directory to path to resolve app module imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

# Keep tests independent from developer local Postgres state.
os.environ["DATABASE_URL"] = "sqlite:///./test_theft_detection.db"

from app.main import app
from app.database import init_db

# Ensure schema exists before endpoint tests execute.
init_db()

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "healthy"


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_get_alerts():
    """Test get alerts endpoint."""
    response = client.get("/api/alerts/")
    assert response.status_code == 200
    assert "alerts" in response.json()
    assert "total" in response.json()


def test_get_statistics():
    """Test statistics endpoint."""
    response = client.get("/api/stats/")
    assert response.status_code == 200
    data = response.json()
    assert "total_alerts" in data
    assert "average_suspicion_score" in data


def test_get_alert_not_found():
    """Test getting non-existent alert."""
    response = client.get("/api/alerts/99999")
    assert response.status_code == 404


def test_annotated_video_head_not_found():
    """HEAD probe should return 404 while annotated video is not available."""
    response = client.head("/api/videos/annotated/non-existent-job")
    assert response.status_code == 404


def test_annotated_video_method_not_allowed_for_post():
    """Annotated endpoint should not accept methods other than GET/HEAD."""
    response = client.post("/api/videos/annotated/non-existent-job")
    assert response.status_code == 405
