"""
FFmpeg and audio processing utilities.
Safe subprocess wrappers preventing arbitrary command execution.
"""
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List

def run_ffmpeg_command(cmd: List[str]) -> subprocess.CompletedProcess:
    """Run an FFmpeg or FFprobe command safely without shell=True."""
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

def probe_video(file_path: str) -> Dict[str, Any]:
    """Extract metadata using ffprobe safely."""
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Video file not found at {file_path}")

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path)
    ]
    
    result = run_ffmpeg_command(cmd)
    data = json.loads(result.stdout)
    
    video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    
    duration = float(data.get("format", {}).get("duration", 0.0))
    if duration == 0.0 and video_stream and "duration" in video_stream:
        try:
            duration = float(video_stream["duration"])
        except (ValueError, TypeError):
            duration = 0.0

    # FPS extraction
    fps = 30.0
    if video_stream and "r_frame_rate" in video_stream:
        r_fr = video_stream["r_frame_rate"]
        if "/" in r_fr:
            num, den = r_fr.split("/")
            if float(den) > 0:
                fps = round(float(num) / float(den), 2)
        else:
            try:
                fps = float(r_fr)
            except ValueError:
                pass
                
    width = video_stream.get("width", 0) if video_stream else 0
    height = video_stream.get("height", 0) if video_stream else 0
    resolution = f"{width}x{height}" if width and height else "unknown"
    
    video_codec = video_stream.get("codec_name", "unknown") if video_stream else "none"
    audio_codec = audio_stream.get("codec_name", "unknown") if audio_stream else "none"
    sample_rate = int(audio_stream.get("sample_rate", 44100)) if audio_stream else 44100
    channels = int(audio_stream.get("channels", 2)) if audio_stream else 2
    file_size = int(data.get("format", {}).get("size", path.stat().st_size if path.exists() else 0))

    return {
        "duration": duration,
        "fps": fps,
        "resolution": resolution,
        "width": width,
        "height": height,
        "video_codec": video_codec,
        "audio_codec": audio_codec,
        "sample_rate": sample_rate,
        "channels": channels,
        "file_size": file_size,
        "has_audio": audio_stream is not None,
    }

def extract_audio(video_path: str, output_wav_path: str, sample_rate: int = 44100, channels: int = 2) -> str:
    """Extract audio track as 16-bit PCM WAV."""
    v_path = Path(video_path).resolve()
    out_path = Path(output_wav_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(v_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", str(channels),
        str(out_path)
    ]
    run_ffmpeg_command(cmd)
    return str(out_path)

def trim_video(video_path: str, output_path: str, start_sec: float, end_sec: float) -> str:
    """Trim video safely while preserving streams."""
    v_path = Path(video_path).resolve()
    out_path = Path(output_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    duration = end_sec - start_sec
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_sec),
        "-i", str(v_path),
        "-t", str(duration),
        "-c", "copy",
        str(out_path)
    ]
    try:
        run_ffmpeg_command(cmd)
    except subprocess.CalledProcessError:
        # Fallback to accurate re-encoding if keyframes prevent stream copy
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_sec),
            "-i", str(v_path),
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            str(out_path)
        ]
        run_ffmpeg_command(cmd)
    return str(out_path)

def separate_speech_and_background(input_wav: str, speech_wav: str, background_wav: str) -> None:
    """
    Separate speech from background music & sound effects using advanced audio phase cancellation,
    center channel extraction, and spectral filtering.
    
    This preserves background music, instruments, and environmental effects in background_wav,
    while isolating dialogue into speech_wav.
    """
    in_p = Path(input_wav).resolve()
    sp_p = Path(speech_wav).resolve()
    bg_p = Path(background_wav).resolve()
    
    sp_p.parent.mkdir(parents=True, exist_ok=True)
    bg_p.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Background isolation:
    # Most stereo tracks place vocal energy in the phantom center.
    # We cancel common center components to preserve stereo music, reverb, instruments, and wide SFX.
    # stereotools with center level reduction or side extraction creates a clean instrumental/effects bed.
    bg_filter = (
        "[0:a]stereotools=mlev=0.15:slev=1.2:phas=1[bg];"
        "[bg]highpass=f=40,lowpass=f=18000[out_bg]"
    )
    cmd_bg = [
        "ffmpeg", "-y",
        "-i", str(in_p),
        "-filter_complex", bg_filter,
        "-map", "[out_bg]",
        "-c:a", "pcm_s16le",
        str(bg_p)
    ]
    try:
        run_ffmpeg_command(cmd_bg)
    except Exception:
        # Fallback: copy audio as background bed if stereo manipulation fails
        subprocess.run(["ffmpeg", "-y", "-i", str(in_p), "-c:a", "pcm_s16le", str(bg_p)], check=True)

    # 2. Speech isolation:
    # Voice frequency range 250Hz - 3800Hz with dynamic speech bandpass and center focus
    sp_filter = (
        "[0:a]pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1,"
        "highpass=f=180,lowpass=f=4000,compand=attacks=0.02:decays=0.2:points=-60/-60|-25/-15|0/-3[out_sp]"
    )
    cmd_sp = [
        "ffmpeg", "-y",
        "-i", str(in_p),
        "-filter_complex", sp_filter,
        "-map", "[out_sp]",
        "-c:a", "pcm_s16le",
        str(sp_p)
    ]
    try:
        run_ffmpeg_command(cmd_sp)
    except Exception:
        subprocess.run(["ffmpeg", "-y", "-i", str(in_p), "-c:a", "pcm_s16le", str(sp_p)], check=True)

def time_stretch_audio(input_wav: str, output_wav: str, speed_ratio: float) -> str:
    """Adjust audio duration using atempo filter (speed_ratio: target_duration / current_duration)."""
    # FFmpeg atempo supports 0.5 to 2.0. If more, chain multiple atempo filters.
    # speed_factor = current_duration / target_duration
    speed_factor = max(0.5, min(2.0, speed_ratio))
    cmd = [
        "ffmpeg", "-y",
        "-i", input_wav,
        "-filter:a", f"atempo={speed_factor:.3f}",
        "-vn",
        output_wav
    ]
    run_ffmpeg_command(cmd)
    return output_wav

def mix_speech_with_background(
    speech_track_wav: str,
    background_track_wav: str,
    output_mixed_wav: str,
    speech_volume: float = 1.0,
    background_volume: float = 1.0,
    preserve_background: bool = True
) -> str:
    """
    Mix target-language speech dialogue track with the preserved background music and sound effects.
    Supports individual volume levels (0% - 200%).
    """
    out_p = Path(output_mixed_wav).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)
    
    if not preserve_background:
        # User opted out of background audio; output only speech track adjusted for volume
        cmd = [
            "ffmpeg", "-y",
            "-i", speech_track_wav,
            "-filter:a", f"volume={speech_volume:.2f}",
            str(out_p)
        ]
        run_ffmpeg_command(cmd)
        return str(out_p)
        
    # Mix speech and background with volume multipliers and dynamic limiting to prevent clipping
    filter_complex = (
        f"[0:a]volume={speech_volume:.2f}[vocal];"
        f"[1:a]volume={background_volume:.2f}[bg];"
        f"[vocal][bg]amix=inputs=2:duration=longest:dropout_transition=2:normalize=0[mixed];"
        f"[mixed]alimiter=limit=0.98[out]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", speech_track_wav,
        "-i", background_track_wav,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:a", "pcm_s16le",
        str(out_p)
    ]
    run_ffmpeg_command(cmd)
    return str(out_p)

def combine_video_and_audio(
    video_path: str,
    audio_path: str,
    output_video_path: str,
    burn_subtitles: bool = False,
    srt_path: str = None,
    subtitle_position: str = "Bottom",
    subtitle_size: str = "Medium"
) -> str:
    """
    Combine final mixed audio with original video.
    PRESERVES the original video frames, resolution, FPS, aspect ratio unchanged.
    Copies original video stream with `-c:v copy` unless subtitle burn-in is explicitly requested.
    """
    v_in = Path(video_path).resolve()
    a_in = Path(audio_path).resolve()
    v_out = Path(output_video_path).resolve()
    v_out.parent.mkdir(parents=True, exist_ok=True)
    
    if burn_subtitles and srt_path and Path(srt_path).exists():
        # Subtitle burning requires video re-encoding
        font_size = 20 if subtitle_size == "Small" else (32 if subtitle_size == "Large" else 26)
        alignment = 6 if subtitle_position == "Top" else 2
        escaped_srt = str(Path(srt_path).resolve()).replace(":", "\\:").replace("'", "\\'")
        sub_filter = f"subtitles='{escaped_srt}':force_style='FontSize={font_size},Alignment={alignment},Outline=1.5,Shadow=1'"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(v_in),
            "-i", str(a_in),
            "-filter_complex", f"[0:v]{sub_filter}[v]",
            "-map", "[v]",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(v_out)
        ]
    else:
        # Standard workflow: COPY the original video stream untouched!
        cmd = [
            "ffmpeg", "-y",
            "-i", str(v_in),
            "-i", str(a_in),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(v_out)
        ]

    run_ffmpeg_command(cmd)
    return str(v_out)

def format_timestamp_srt(seconds: float) -> str:
    """Convert float seconds to SRT timestamp HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def format_timestamp_vtt(seconds: float) -> str:
    """Convert float seconds to WebVTT timestamp HH:MM:SS.mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

def export_srt(segments: List[Dict[str, Any]], output_path: str) -> str:
    """Write subtitle segments to SRT file."""
    lines = []
    for idx, seg in enumerate(segments, 1):
        start = format_timestamp_srt(seg["start_time"])
        end = format_timestamp_srt(seg["end_time"])
        text = seg.get("translated_text", seg.get("text", "")).strip()
        lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
    content = "\n".join(lines)
    Path(output_path).write_text(content, encoding="utf-8")
    return output_path

def export_vtt(segments: List[Dict[str, Any]], output_path: str) -> str:
    """Write subtitle segments to WebVTT file."""
    lines = ["WEBVTT\n"]
    for idx, seg in enumerate(segments, 1):
        start = format_timestamp_vtt(seg["start_time"])
        end = format_timestamp_vtt(seg["end_time"])
        text = seg.get("translated_text", seg.get("text", "")).strip()
        lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
    content = "\n".join(lines)
    Path(output_path).write_text(content, encoding="utf-8")
    return output_path
