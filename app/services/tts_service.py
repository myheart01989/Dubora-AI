"""
Text-To-Speech (TTS) service with voice customization and timing synchronization.
Generates target-language speech segments and places them on the master timeline.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os
import subprocess
from pathlib import Path
from gtts import gTTS

from app.config import settings
from app.utils.ffmpeg_utils import probe_video, time_stretch_audio, run_ffmpeg_command

# Language mapping for TTS engines
TTS_LANG_MAP = {
    "en": "en",
    "te": "te",
    "hi": "hi",
    "ta": "ta",
    "kn": "kn",
    "ml": "ml",
    "mr": "mr",
    "bn": "bn",
    "gu": "gu",
    "pa": "pa",
    "ur": "ur",
    "es": "es",
    "fr": "fr",
    "de": "de",
    "it": "it",
    "pt": "pt",
    "ja": "ja",
    "ko": "ko",
    "zh": "zh-CN",
    "ar": "ar",
    "ru": "ru",
}

class TTSProvider(ABC):
    @abstractmethod
    def generate_speech_segment(
        self,
        text: str,
        target_lang: str,
        output_wav: str,
        voice_gender: str = "Female",
        voice_style: str = "Natural",
        pitch: str = "Normal"
    ) -> str:
        pass

class GTTSProvider(TTSProvider):
    def generate_speech_segment(
        self,
        text: str,
        target_lang: str,
        output_wav: str,
        voice_gender: str = "Female",
        voice_style: str = "Natural",
        pitch: str = "Normal"
    ) -> str:
        lang_code = TTS_LANG_MAP.get(target_lang, "en")
        temp_mp3 = Path(output_wav).with_suffix(".temp.mp3")
        
        # Generate with gTTS
        tts = gTTS(text=text, lang=lang_code, slow=False)
        tts.save(str(temp_mp3))
        
        # Audio filter for pitch and gender characteristics
        # Male pitch shift slightly down, Female normal/slightly up
        pitch_val = 1.0
        if voice_gender.lower() == "male":
            pitch_val = 0.88
        elif voice_gender.lower() == "female":
            pitch_val = 1.08
            
        if pitch == "Low":
            pitch_val *= 0.92
        elif pitch == "High":
            pitch_val *= 1.12

        # Convert to WAV with resample & pitch adjustment
        filter_str = f"asetrate=44100*{pitch_val:.2f},aresample=44100" if pitch_val != 1.0 else "anull"
        cmd = [
            "ffmpeg", "-y",
            "-i", str(temp_mp3),
            "-af", filter_str,
            "-acodec", "pcm_s16le",
            "-ar", "44100",
            "-ac", "2",
            str(output_wav)
        ]
        run_ffmpeg_command(cmd)
        temp_mp3.unlink(missing_ok=True)
        return output_wav

class TTSService:
    def __init__(self):
        self.provider = GTTSProvider()

    def generate_and_sync_speech(
        self,
        translations: List[Dict[str, Any]],
        target_lang: str,
        job_id: str,
        total_duration: float,
        voice_gender: str = "Female",
        voice_style: str = "Natural",
        speaking_speed: float = 1.0,
        voice_pitch: str = "Normal"
    ) -> str:
        """
        1. Generate audio segment for each translated sentence.
        2. Synchronize speech to fit inside the original dialogue segment without unnatural acceleration.
        3. Assemble onto a synchronized dialogue master track matching total_duration.
        """
        output_dir = settings.GENERATED_VOICE_DIR / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        synchronized_segments = []

        for idx, item in enumerate(translations):
            text = item.get("translated_text", "").strip()
            if not text:
                continue

            orig_start = float(item["start_time"])
            orig_end = float(item["end_time"])
            slot_duration = max(0.5, orig_end - orig_start)

            raw_segment_path = str(output_dir / f"seg_{idx}_raw.wav")
            synced_segment_path = str(output_dir / f"seg_{idx}_synced.wav")

            # Generate TTS audio
            self.provider.generate_speech_segment(
                text=text,
                target_lang=target_lang,
                output_wav=raw_segment_path,
                voice_gender=voice_gender,
                voice_style=voice_style,
                pitch=voice_pitch
            )

            # Measure generated segment duration
            meta = probe_video(raw_segment_path)
            gen_duration = meta["duration"]

            # Compute speed synchronization factor
            # If gen_duration > slot_duration: we need to speed up slightly (max 1.4x)
            # Apply user speaking_speed multiplier as well
            base_ratio = gen_duration / slot_duration
            effective_speed = max(0.8, min(1.4, base_ratio * speaking_speed))

            time_stretch_audio(raw_segment_path, synced_segment_path, effective_speed)

            synchronized_segments.append({
                "start": orig_start,
                "file": synced_segment_path,
                "duration": min(slot_duration * 1.15, gen_duration / effective_speed)
            })

        # Assemble full dialogue track with accurate timestamps using FFmpeg adelay & amix
        dialogue_master_wav = str(settings.GENERATED_VOICE_DIR / f"{job_id}_dialogue_master.wav")
        self._assemble_dialogue_timeline(synchronized_segments, dialogue_master_wav, total_duration)

        return dialogue_master_wav

    def _assemble_dialogue_timeline(
        self,
        segments: List[Dict[str, Any]],
        output_path: str,
        total_duration: float
    ) -> None:
        """Place every dialogue chunk at its exact timestamp onto the silent master canvas."""
        if not segments:
            # Create a silent audio track of total_duration
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"anullsrc=r=44100:cl=stereo",
                "-t", str(total_duration),
                "-c:a", "pcm_s16le",
                output_path
            ]
            run_ffmpeg_command(cmd)
            return

        # Build FFmpeg complex filter using adelay and amix
        inputs = []
        filter_parts = []
        
        # Base silence track as input 0
        inputs.extend(["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo"])
        filter_parts.append(f"[0:a]atrim=0:{total_duration}[base]")
        
        mix_inputs = ["[base]"]

        for i, seg in enumerate(segments, start=1):
            inputs.extend(["-i", seg["file"]])
            delay_ms = int(round(seg["start"] * 1000))
            filter_parts.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[del{i}]")
            mix_inputs.append(f"[del{i}]")

        total_mix_count = len(mix_inputs)
        filter_parts.append(
            f"{''.join(mix_inputs)}amix=inputs={total_mix_count}:duration=first:dropout_transition=0:normalize=0[out]"
        )

        filter_complex = ";".join(filter_parts)
        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-t", str(total_duration),
            "-c:a", "pcm_s16le",
            output_path
        ]
        run_ffmpeg_command(cmd)
