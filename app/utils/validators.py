"""
Validation utilities for files, URLs, languages, and durations.
"""
import re
from pathlib import Path
from typing import Tuple, Optional
from urllib.parse import urlparse

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}

SUPPORTED_LANGUAGES = [
    {"code": "auto", "name": "Auto Detect"},
    {"code": "en", "name": "English"},
    {"code": "te", "name": "Telugu"},
    {"code": "hi", "name": "Hindi"},
    {"code": "ta", "name": "Tamil"},
    {"code": "kn", "name": "Kannada"},
    {"code": "ml", "name": "Malayalam"},
    {"code": "mr", "name": "Marathi"},
    {"code": "bn", "name": "Bengali"},
    {"code": "gu", "name": "Gujarati"},
    {"code": "pa", "name": "Punjabi"},
    {"code": "ur", "name": "Urdu"},
    {"code": "es", "name": "Spanish"},
    {"code": "fr", "name": "French"},
    {"code": "de", "name": "German"},
    {"code": "it", "name": "Italian"},
    {"code": "pt", "name": "Portuguese"},
    {"code": "ja", "name": "Japanese"},
    {"code": "ko", "name": "Korean"},
    {"code": "zh", "name": "Chinese"},
    {"code": "ar", "name": "Arabic"},
    {"code": "ru", "name": "Russian"},
]

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and special character issues."""
    name = Path(filename).name
    name = re.sub(r'[^a-zA-Z0-9_.-]', '_', name)
    return name if name else "video.mp4"

def validate_video_file(filename: str, file_size: int, max_size_mb: int) -> Tuple[bool, Optional[str]]:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported video format: '{ext}'. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"
    
    max_bytes = max_size_mb * 1024 * 1024
    if file_size > max_bytes:
        return False, f"File size ({file_size / (1024*1024):.1f}MB) exceeds limit of {max_size_mb}MB"
        
    return True, None

def validate_youtube_url(url: str) -> Tuple[bool, Optional[str]]:
    """Validate YouTube URL and guard against SSRF or malicious inputs."""
    if not url or not isinstance(url, str):
        return False, "YouTube URL cannot be empty."
    
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        return False, "Invalid URL scheme. Must be http or https."
    
    netloc = parsed.netloc.lower()
    if not any(domain in netloc for domain in ["youtube.com", "youtu.be", "www.youtube.com", "m.youtube.com"]):
        return False, "Invalid domain. Only YouTube URLs are supported."
    
    # Specific video ID check
    yt_regex = r'^(https?://)?(www\.|m\.)?(youtube\.com/(watch\?v=|embed/|shorts/|v/)|youtu\.be/)([\w-]{11})([?&].*)?$'
    match = re.match(yt_regex, url.strip())
    if not match:
        return False, "Invalid YouTube video link format. Please provide a standard YouTube video or Shorts link."
    
    return True, None

def validate_languages(orig_lang: str, target_lang: str) -> Tuple[bool, Optional[str]]:
    valid_codes = {item["code"] for item in SUPPORTED_LANGUAGES}
    
    if orig_lang != "auto" and orig_lang not in valid_codes:
        return False, f"Unsupported original language: {orig_lang}"
    if target_lang not in valid_codes or target_lang == "auto":
        return False, f"Target language must be a specific valid language code, got '{target_lang}'"
        
    if orig_lang.lower() == target_lang.lower():
        return False, "Original Language and Target Language cannot be identical."
        
    return True, None

def parse_time_to_seconds(time_str: str) -> float:
    """Parse HH:MM:SS or MM:SS to seconds."""
    parts = time_str.strip().split(":")
    if len(parts) == 3:
        h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
        return h * 3600 + m * 60 + s
    elif len(parts) == 2:
        m, s = float(parts[0]), float(parts[1])
        return m * 60 + s
    elif len(parts) == 1:
        return float(parts[0])
    return 0.0

def format_seconds_to_time(seconds: float) -> str:
    """Format seconds to HH:MM:SS."""
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
