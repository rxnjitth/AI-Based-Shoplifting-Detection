"""
RTSP camera endpoints — connect/disconnect/status for EZVIZ and other
RTSP-capable cameras.
"""
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import Optional, Dict

from app.services.rtsp_stream import rtsp_manager, StreamStatus
from app.database import get_db
from app.config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ConnectRequest(BaseModel):
    camera_id: str                  # Arbitrary label, e.g. "entrance"
    rtsp_url: str                   # Full RTSP URL
    # Convenience fields — if rtsp_url is empty these are used to build it
    ip: Optional[str] = None
    port: int = 554
    username: Optional[str] = None
    password: Optional[str] = None
    channel: int = 1
    stream: str = "main"            # "main" or "sub"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_rtsp_url(req: ConnectRequest) -> str:
    """Build EZVIZ RTSP URL from components if rtsp_url not provided."""
    if req.rtsp_url:
        return req.rtsp_url
    if not req.ip:
        raise HTTPException(
            status_code=400,
            detail="Provide either rtsp_url or ip/username/password"
        )
    creds = ""
    if req.username and req.password:
        creds = f"{req.username}:{req.password}@"
    stream_path = "main" if req.stream == "main" else "sub"
    # Support both EZVIZ path formats:
    #   New:  /h264/ch{n}/main/av_stream
    #   Old:  /ch{n}/main  (used by older EZVIZ firmware)
    return (
        f"rtsp://{creds}{req.ip}:{req.port}"
        f"/ch{req.channel}/{stream_path}"
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/connect")
async def connect_camera(req: ConnectRequest):
    """
    Start streaming from an EZVIZ (or any RTSP) camera.

    You can either pass a full ``rtsp_url`` or let the server build one from
    ``ip``, ``port``, ``username``, ``password``, ``channel``, and ``stream``.
    """
    rtsp_url = _build_rtsp_url(req)

    state = rtsp_manager.start(
        camera_id=req.camera_id,
        rtsp_url=rtsp_url,
        on_alert=None,          # handled inside the worker
        get_db_session=get_db,
    )

    return {
        "camera_id": req.camera_id,
        "rtsp_url": rtsp_url,
        "status": state.status,
        "message": f"Stream started for camera '{req.camera_id}'",
    }


@router.delete("/disconnect/{camera_id}")
async def disconnect_camera(camera_id: str):
    """Stop streaming from a camera."""
    stopped = rtsp_manager.stop(camera_id)
    if not stopped:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    return {"camera_id": camera_id, "message": "Stream stopped"}


@router.get("/status/{camera_id}")
async def camera_status(camera_id: str):
    """Get current stream status and stats for a camera."""
    state = rtsp_manager.get_state(camera_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    return {
        "camera_id": camera_id,
        "status": state.status,
        "error": state.error,
        "frames_processed": state.frames_processed,
        "alerts_generated": state.alerts_generated,
        "fps": state.fps,
        "uptime_seconds": (
            round(__import__("time").time() - state.started_at, 1)
            if state.started_at else 0
        ),
    }


@router.get("/cameras")
async def list_cameras():
    """List all registered camera streams and their statuses."""
    cameras = rtsp_manager.list_cameras()
    return {
        "cameras": [
            {
                "camera_id": cid,
                "status": s.status,
                "fps": s.fps,
                "frames_processed": s.frames_processed,
                "alerts_generated": s.alerts_generated,
            }
            for cid, s in cameras.items()
        ]
    }


@router.get("/default-camera")
async def get_default_camera():
    """
    Return the default camera config from .env so the frontend
    can pre-fill the connection form.
    """
    return {
        "camera_id": settings.ezviz_camera_id,
        "rtsp_url": settings.ezviz_rtsp_url,
        "port": settings.ezviz_default_port,
        "channel": settings.ezviz_default_channel,
        "stream": settings.ezviz_default_stream,
    }


@router.get("/preview/{camera_id}")
async def preview_frame(camera_id: str):
    """
    Return the latest JPEG frame from a running camera stream.
    Useful for a live thumbnail in the dashboard.
    """
    jpg = rtsp_manager.get_latest_frame(camera_id)
    if jpg is None:
        raise HTTPException(
            status_code=404,
            detail=f"No frame available for camera '{camera_id}'"
        )
    return Response(content=jpg, media_type="image/jpeg")
