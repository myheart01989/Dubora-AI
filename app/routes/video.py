"""
Video upload and YouTube ingestion API endpoints.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

from app.database import get_db
from app.models.models import Video
from app.services.video_service import VideoService

router = APIRouter(prefix="/api/video", tags=["video"])

class YouTubeRequest(BaseModel):
    url: str

@router.post("/upload")
async def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a video file (MP4, MOV, MKV, AVI, WEBM)."""
    try:
        data = VideoService.save_uploaded_file(file.file, file.filename)
        
        video_rec = Video(
            id=data["id"],
            filename=data["filename"],
            original_name=data["original_name"],
            duration=data["duration"],
            fps=data["fps"],
            resolution=data["resolution"],
            audio_codec=data["audio_codec"],
            video_codec=data["video_codec"],
            sample_rate=data["sample_rate"],
            channels=data["channels"],
            file_size=data["file_size"],
            storage_path=data["storage_path"],
            source_type="upload",
        )
        db.add(video_rec)
        db.commit()
        db.refresh(video_rec)
        
        return {
            "status": "success",
            "video": {
                "id": video_rec.id,
                "filename": video_rec.filename,
                "original_name": video_rec.original_name,
                "duration": video_rec.duration,
                "fps": video_rec.fps,
                "resolution": video_rec.resolution,
                "audio_codec": video_rec.audio_codec,
                "video_codec": video_rec.video_codec,
                "sample_rate": video_rec.sample_rate,
                "channels": video_rec.channels,
                "file_size": video_rec.file_size,
                "has_audio": data["has_audio"],
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/youtube")
async def load_youtube_video(req: YouTubeRequest, db: Session = Depends(get_db)):
    """Ingest a public YouTube video."""
    try:
        data = VideoService.download_youtube_video(req.url)
        
        video_rec = Video(
            id=data["id"],
            filename=data["filename"],
            original_name=data["original_name"],
            duration=data["duration"],
            fps=data["fps"],
            resolution=data["resolution"],
            audio_codec=data["audio_codec"],
            video_codec=data["video_codec"],
            sample_rate=data["sample_rate"],
            channels=data["channels"],
            file_size=data["file_size"],
            storage_path=data["storage_path"],
            source_type="youtube",
            youtube_url=req.url,
        )
        db.add(video_rec)
        db.commit()
        db.refresh(video_rec)
        
        return {
            "status": "success",
            "video": {
                "id": video_rec.id,
                "filename": video_rec.filename,
                "original_name": video_rec.original_name,
                "duration": video_rec.duration,
                "fps": video_rec.fps,
                "resolution": video_rec.resolution,
                "audio_codec": video_rec.audio_codec,
                "video_codec": video_rec.video_codec,
                "sample_rate": video_rec.sample_rate,
                "channels": video_rec.channels,
                "file_size": video_rec.file_size,
                "has_audio": data["has_audio"],
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{video_id}")
async def get_video_info(video_id: str, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    return {
        "id": video.id,
        "filename": video.filename,
        "original_name": video.original_name,
        "duration": video.duration,
        "fps": video.fps,
        "resolution": video.resolution,
        "audio_codec": video.audio_codec,
        "video_codec": video.video_codec,
        "sample_rate": video.sample_rate,
        "channels": video.channels,
        "file_size": video.file_size,
        "source_type": video.source_type,
        "youtube_url": video.youtube_url,
    }

@router.delete("/{video_id}")
async def delete_video(video_id: str, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        Path(video.storage_path).unlink(missing_ok=True)
    except Exception:
        pass

    db.delete(video)
    db.commit()
    return {"status": "success", "message": "Video deleted successfully"}
