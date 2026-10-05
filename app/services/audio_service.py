"""
Audio service for extracting audio and managing audio properties.
"""
from pathlib import Path
from typing import Dict, Any
from app.config import settings
from app.utils.ffmpeg_utils import extract_audio, probe_video

class AudioService:
    @staticmethod
    def extract_audio_from_video(video_path: str, job_id: str) -> str:
        """Extract audio track as 16-bit 44.1kHz stereo PCM WAV."""
        output_filename = f"{job_id}_extracted.wav"
        output_path = settings.EXTRACTED_AUDIO_DIR / output_filename
        return extract_audio(video_path, str(output_path))
