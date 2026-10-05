"""
Rendering service for final audio mixing, subtitle export, and video muxing.
Ensures zero degradation of original video stream by copying video frames directly.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.config import settings
from app.utils.ffmpeg_utils import (
    mix_speech_with_background,
    combine_video_and_audio,
    export_srt,
    export_vtt,
)

class RenderingService:
    @staticmethod
    def mix_final_audio(
        speech_wav: str,
        background_wav: str,
        job_id: str,
        voice_volume: float = 1.0,
        background_volume: float = 1.0,
        preserve_background: bool = True
    ) -> str:
        """Mix dialogue track with preserved background music and effects."""
        output_mixed_path = str(settings.TEMP_DIR / f"{job_id}_final_mixed.wav")
        return mix_speech_with_background(
            speech_track_wav=speech_wav,
            background_track_wav=background_wav,
            output_mixed_wav=output_mixed_path,
            speech_volume=voice_volume,
            background_volume=background_volume,
            preserve_background=preserve_background
        )

    @staticmethod
    def generate_subtitles(
        transcripts: List[Dict[str, Any]],
        translations: List[Dict[str, Any]],
        job_id: str
    ) -> Dict[str, str]:
        """Generate SRT, VTT, and TXT transcripts."""
        srt_path = str(settings.TRANSCRIPTS_DIR / f"{job_id}_translated.srt")
        vtt_path = str(settings.TRANSCRIPTS_DIR / f"{job_id}_translated.vtt")
        orig_txt_path = str(settings.TRANSCRIPTS_DIR / f"{job_id}_original.txt")
        trans_txt_path = str(settings.TRANSLATIONS_DIR / f"{job_id}_translated.txt")

        # Subtitles
        export_srt(translations, srt_path)
        export_vtt(translations, vtt_path)

        # Original transcript plain text
        orig_lines = [f"[{t['start_time']:.2f}s - {t['end_time']:.2f}s] {t.get('text', t.get('original_text', ''))}" for t in transcripts]
        Path(orig_txt_path).write_text("\n".join(orig_lines), encoding="utf-8")

        # Translated transcript plain text
        trans_lines = [f"[{t['start_time']:.2f}s - {t['end_time']:.2f}s] {t.get('translated_text', '')}" for t in translations]
        Path(trans_txt_path).write_text("\n".join(trans_lines), encoding="utf-8")

        return {
            "srt": srt_path,
            "vtt": vtt_path,
            "original_txt": orig_txt_path,
            "translated_txt": trans_txt_path,
        }

    @staticmethod
    def export_final_video(
        video_path: str,
        audio_path: str,
        job_id: str,
        burn_subtitles: bool = False,
        srt_path: Optional[str] = None,
        subtitle_position: str = "Bottom",
        subtitle_size: str = "Medium"
    ) -> str:
        """
        Produce the final video file.
        Uses `-c:v copy` when possible to preserve untouched video frames, FPS, and resolution.
        """
        output_filename = f"{job_id}_converted.mp4"
        output_path = settings.FINAL_VIDEOS_DIR / output_filename
        
        return combine_video_and_audio(
            video_path=video_path,
            audio_path=audio_path,
            output_video_path=str(output_path),
            burn_subtitles=burn_subtitles,
            srt_path=srt_path,
            subtitle_position=subtitle_position,
            subtitle_size=subtitle_size
        )
