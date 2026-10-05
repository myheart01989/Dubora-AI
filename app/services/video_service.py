"""
Video service for handling file uploads, YouTube fetching, duration validation, and trimming.
"""
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import subprocess

from app.config import settings
from app.utils.validators import sanitize_filename, validate_video_file, validate_youtube_url
from app.utils.ffmpeg_utils import probe_video, trim_video

class VideoService:
    @staticmethod
    def save_uploaded_file(file_obj, original_filename: str) -> Dict[str, Any]:
        """Save uploaded video file and probe its metadata."""
        safe_name = sanitize_filename(original_filename)
        video_id = str(uuid.uuid4())
        dest_filename = f"{video_id}_{safe_name}"
        dest_path = settings.UPLOAD_DIR / dest_filename

        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file_obj, buffer)

        file_size = dest_path.stat().st_size
        valid, err = validate_video_file(original_filename, file_size, settings.MAX_UPLOAD_SIZE_MB)
        if not valid:
            dest_path.unlink(missing_ok=True)
            raise ValueError(err)

        metadata = probe_video(str(dest_path))
        return {
            "id": video_id,
            "filename": dest_filename,
            "original_name": original_filename,
            "storage_path": str(dest_path),
            "file_size": file_size,
            "source_type": "upload",
            "youtube_url": None,
            **metadata,
        }

    @staticmethod
    def download_youtube_video(url: str) -> Dict[str, Any]:
        """Download YouTube video using yt-dlp safely and probe metadata."""
        valid, err = validate_youtube_url(url)
        if not valid:
            raise ValueError(err)

        video_id = str(uuid.uuid4())
        output_template = str(settings.UPLOAD_DIR / f"{video_id}_%(title).50s.%(ext)s")
        
        # Download best video + audio up to 1080p in MP4 container
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--max-filesize", f"{settings.MAX_UPLOAD_SIZE_MB}M",
            "-f", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "-o", output_template,
            url.strip()
        ]
        
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"YouTube download failed: {e.stderr or e.stdout or 'Video unavailable or restricted'}")

        # Find downloaded file
        matched = list(settings.UPLOAD_DIR.glob(f"{video_id}_*"))
        if not matched:
            raise FileNotFoundError("Downloaded YouTube video file not found on disk.")
            
        dest_path = matched[0]
        metadata = probe_video(str(dest_path))
        
        return {
            "id": video_id,
            "filename": dest_path.name,
            "original_name": dest_path.name.replace(f"{video_id}_", ""),
            "storage_path": str(dest_path),
            "file_size": dest_path.stat().st_size,
            "source_type": "youtube",
            "youtube_url": url,
            **metadata,
        }

    @staticmethod
    def enforce_duration_limit(
        video_path: str,
        max_duration: int,
        trim_start: float = 0.0,
        trim_end: Optional[float] = None
    ) -> Dict[str, Any]:
        """Validate and apply duration limits or trimming."""
        meta = probe_video(video_path)
        total_duration = meta["duration"]
        
        start_sec = max(0.0, trim_start)
        end_sec = min(total_duration, trim_end) if (trim_end and trim_end > start_sec) else total_duration

        effective_duration = end_sec - start_sec
        needs_trim = False

        if trim_start > 0.0 or (trim_end is not None and trim_end < total_duration):
            needs_trim = True
        elif max_duration > 0 and effective_duration > max_duration:
            end_sec = start_sec + max_duration
            needs_trim = True

        if needs_trim:
            trimmed_filename = f"trimmed_{Path(video_path).name}"
            trimmed_path = settings.TEMP_DIR / trimmed_filename
            trim_video(video_path, str(trimmed_path), start_sec, end_sec)
            trimmed_meta = probe_video(str(trimmed_path))
            return {
                "trimmed": True,
                "path": str(trimmed_path),
                "duration": trimmed_meta["duration"],
                "start": start_sec,
                "end": end_sec,
            }
            
        return {
            "trimmed": False,
            "path": video_path,
            "duration": total_duration,
            "start": start_sec,
            "end": end_sec,
        }
