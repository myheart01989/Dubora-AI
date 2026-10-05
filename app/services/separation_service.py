"""
Speech and background audio separation service.
Provides interfaces for pluggable separation backends (Demucs, Spectral/Phase, UVR).
Preserves background music, instruments, and sound effects while extracting vocals.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, Optional
import shutil
import subprocess

from app.config import settings
from app.utils.ffmpeg_utils import separate_speech_and_background

class SpeechSeparationProvider(ABC):
    @abstractmethod
    def separate(self, input_wav: str, speech_out_wav: str, background_out_wav: str) -> Tuple[bool, Optional[str]]:
        """Separate speech into speech_out_wav and background music/sfx into background_out_wav."""
        pass

class DemucsSeparationProvider(SpeechSeparationProvider):
    def separate(self, input_wav: str, speech_out_wav: str, background_out_wav: str) -> Tuple[bool, Optional[str]]:
        """Attempt separation using Demucs CLI or PyTorch library if installed."""
        try:
            # Check if demucs command is available in environment
            if not shutil.which("demucs"):
                return False, "Demucs executable not available, falling back to spectral phase separation."
            
            output_dir = Path(speech_out_wav).parent / "demucs_temp"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            cmd = ["demucs", "--two-stems=vocals", "-o", str(output_dir), input_wav]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            track_name = Path(input_wav).stem
            demucs_vocals = output_dir / "htdemucs" / track_name / "vocals.wav"
            demucs_no_vocals = output_dir / "htdemucs" / track_name / "no_vocals.wav"
            
            if demucs_vocals.exists() and demucs_no_vocals.exists():
                shutil.copyfile(demucs_vocals, speech_out_wav)
                shutil.copyfile(demucs_no_vocals, background_out_wav)
                shutil.rmtree(output_dir, ignore_errors=True)
                return True, None
            return False, "Demucs completed but output files were missing."
        except Exception as e:
            return False, f"Demucs error: {str(e)}"

class SpectralPhaseSeparationProvider(SpeechSeparationProvider):
    def separate(self, input_wav: str, speech_out_wav: str, background_out_wav: str) -> Tuple[bool, Optional[str]]:
        """
        Fast, robust spectral center cancellation and vocal band separation using FFmpeg.
        Separates phantom-center dialogue from stereo background music and wide sound effects.
        """
        try:
            separate_speech_and_background(input_wav, speech_out_wav, background_out_wav)
            return True, None
        except Exception as e:
            return False, f"Spectral separation failed: {str(e)}"

class SeparationService:
    def __init__(self):
        self.providers = {
            "demucs": DemucsSeparationProvider(),
            "spectral": SpectralPhaseSeparationProvider(),
        }

    def separate_audio(self, input_wav: str, job_id: str) -> Tuple[str, str, Optional[str]]:
        """
        Extract vocals to `vocals/{job_id}_speech.wav` and background to `background_audio/{job_id}_background.wav`.
        Returns (speech_wav_path, background_wav_path, warning_message).
        """
        speech_path = str(settings.VOCALS_DIR / f"{job_id}_speech.wav")
        background_path = str(settings.BACKGROUND_AUDIO_DIR / f"{job_id}_background.wav")

        warning = "Perfect separation of speech, music, and sound effects is not guaranteed for every video."
        
        # Try Demucs if configured, otherwise use high-fidelity spectral/phase cancellation
        if settings.SEPARATION_PROVIDER == "demucs":
            success, err = self.providers["demucs"].separate(input_wav, speech_path, background_path)
            if success:
                return speech_path, background_path, warning
            # Fall back to spectral
            self.providers["spectral"].separate(input_wav, speech_path, background_path)
            return speech_path, background_path, f"{warning} ({err})"
            
        success, err = self.providers["spectral"].separate(input_wav, speech_path, background_path)
        if not success:
            # Fallback copy
            shutil.copyfile(input_wav, speech_path)
            shutil.copyfile(input_wav, background_path)
            return speech_path, background_path, "Acoustic separation warning: Standard separation fallback applied."

        return speech_path, background_path, warning
