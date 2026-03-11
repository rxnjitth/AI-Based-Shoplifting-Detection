"""
Main FastAPI application entry point.
Initializes the API, database, and routes.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import os

from app.config import settings
from app.database import init_db
from app.models import HealthCheckResponse
from app.routers import alerts, videos, stats, live

# Initialize FastAPI app
app = FastAPI(
    title="Smart Theft Detection API",
    description="Computer vision-based theft detection system API",
    version="0.1.0",
    debug=settings.debug
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(videos.router, prefix="/api/videos", tags=["videos"])
app.include_router(stats.router, prefix="/api/stats", tags=["statistics"])
app.include_router(live.router, prefix="/api/live", tags=["live-detection"])

# Mount static file directories for serving evidence
if os.path.exists(settings.evidence_snapshots_dir):
    app.mount("/evidence/snapshots", StaticFiles(directory=settings.evidence_snapshots_dir), name="snapshots")
if os.path.exists(settings.evidence_clips_dir):
    app.mount("/evidence/clips", StaticFiles(directory=settings.evidence_clips_dir), name="clips")


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    print("🚀 Starting Smart Theft Detection API...")
    
    # Ensure directories exist
    settings.ensure_directories()
    print(f"✅ Created directories")
    
    # Initialize database
    init_db()
    print(f"✅ Database initialized")
    
    print(f"🎯 Server ready at http://{settings.host}:{settings.port}")


@app.get("/", response_model=HealthCheckResponse)
async def root():
    """Root endpoint - health check."""
    return HealthCheckResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.utcnow()
    )


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.utcnow()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
