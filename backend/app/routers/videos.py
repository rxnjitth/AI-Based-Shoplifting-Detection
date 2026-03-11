"""
Video upload and processing API endpoints.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends, Request
from fastapi.responses import Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import uuid
import shutil
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.database import get_db, SessionLocal
from app.models import VideoUploadResponse
from app.services.video_processor import VideoProcessor

router = APIRouter()

# In-memory job status for MVP runtime observability.
JOB_STATUS = {}


async def process_video_task(video_path: str, job_id: str):
    """
    Background task to process uploaded video.
    """
    try:
        JOB_STATUS[job_id] = {
            "status": "processing",
            "message": "Video processing in progress",
        }
        print(f"🎬 Processing video: {video_path} (Job: {job_id})")
        
        # Initialize video processor
        processor = VideoProcessor()
        db_session = SessionLocal()
        
        # Process the video and publish to the path expected by /annotated/{job_id}.
        annotated_output_path = os.path.join(settings.upload_dir, f"{job_id}_annotated.mp4")
        await processor.process_video(video_path, db_session, output_path=annotated_output_path)

        JOB_STATUS[job_id] = {
            "status": "completed",
            "message": "Video processing completed",
        }
        
        print(f"✅ Video processing completed: {job_id}")
        
    except Exception as e:
        annotated_output_path = os.path.join(settings.upload_dir, f"{job_id}_annotated.mp4")
        output_base, output_ext = os.path.splitext(annotated_output_path)
        temp_output_path = f"{output_base}.processing{output_ext or '.mp4'}"
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)

        JOB_STATUS[job_id] = {
            "status": "failed",
            "message": str(e),
        }
        print(f"❌ Error processing video {job_id}: {str(e)}")
    finally:
        if "db_session" in locals():
            db_session.close()


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload a video file for processing.
    The video will be processed asynchronously.
    """
    # Validate file extension
    allowed_extensions = {".mp4", ".avi", ".mov", ".mkv"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Generate unique filename
    job_id = str(uuid.uuid4())
    filename = f"{job_id}{file_ext}"
    file_path = os.path.join(settings.upload_dir, filename)
    
    # Ensure upload directory exists
    os.makedirs(settings.upload_dir, exist_ok=True)
    
    # Save uploaded file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Add background processing task
    JOB_STATUS[job_id] = {
        "status": "queued",
        "message": "Video queued for processing",
    }

    background_tasks.add_task(process_video_task, file_path, job_id)
    
    return VideoUploadResponse(
        job_id=job_id,
        filename=file.filename,
        file_path=file_path,
        message="Video uploaded successfully. Processing started."
    )


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Get the status of a video processing job.
    (Simplified for MVP - in production, use a proper job queue)
    """
    annotated_path = os.path.join(settings.upload_dir, f"{job_id}_annotated.mp4")
    processing_path = os.path.join(settings.upload_dir, f"{job_id}_annotated.processing.mp4")

    tracked_status = JOB_STATUS.get(job_id)
    if tracked_status and tracked_status.get("status") in {"failed", "completed", "queued", "processing"}:
        status = tracked_status
    elif os.path.exists(annotated_path):
        status = {
            "status": "completed",
            "message": "Video processing completed",
        }
    elif os.path.exists(processing_path):
        status = {
            "status": "processing",
            "message": "Video processing in progress",
        }
    else:
        status = {
            "status": "unknown",
            "message": "Job not found",
        }

    return {
        "job_id": job_id,
        **status,
    }


@router.api_route("/annotated/{job_id}", methods=["GET", "HEAD"])
async def get_annotated_video(job_id: str, request: Request):
    """
    Get the annotated video with detection overlays.
    
    Args:
        job_id: The job ID from video upload
        
    Returns:
        Annotated video file
    """
    # Find the annotated video file
    annotated_path = os.path.join(settings.upload_dir, f"{job_id}_annotated.mp4")
    
    if not os.path.exists(annotated_path):
        raise HTTPException(
            status_code=404,
            detail="Annotated video not found. Video may still be processing."
        )
    
    if request.method == "HEAD":
        # Lightweight readiness probe used by the frontend before loading the video.
        return Response(status_code=200, headers={"Content-Type": "video/mp4"})

    return FileResponse(
        path=annotated_path,
        media_type="video/mp4",
        filename=f"{job_id}_annotated.mp4"
    )
