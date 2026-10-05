"""
Application configuration for YouTube Video Language Converter.
Supports environment variables and provides centralized directory management.
"""
import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseModel):
    APP_NAME: str = os.getenv("APP_NAME", "YouTube Video Language Converter")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Storage settings
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    EXTRACTED_AUDIO_DIR: Path = BASE_DIR / "extracted_audio"
    VOCALS_DIR: Path = BASE_DIR / "vocals"
    BACKGROUND_AUDIO_DIR: Path = BASE_DIR / "background_audio"
    TRANSCRIPTS_DIR: Path = BASE_DIR / "transcripts"
    TRANSLATIONS_DIR: Path = BASE_DIR / "translations"
    GENERATED_VOICE_DIR: Path = BASE_DIR / "generated_voice"
    FINAL_VIDEOS_DIR: Path = BASE_DIR / "final_videos"
    TEMP_DIR: Path = BASE_DIR / "temporary_files"
    OUTPUT_DIR: Path = BASE_DIR / "outputs"
    MODELS_DIR: Path = BASE_DIR / "models"
    
    # Limits & Processing defaults
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "1024"))  # 1GB default
    DEFAULT_MAX_DURATION: int = int(os.getenv("DEFAULT_MAX_DURATION", "600"))  # 10 minutes default
    USE_GPU: str = os.getenv("USE_GPU", "auto")
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    OUTPUT_FORMAT: str = os.getenv("OUTPUT_FORMAT", "mp4")
    
    # AI Engine & Provider configuration
    TRANSLATION_PROVIDER: str = os.getenv("TRANSLATION_PROVIDER", "auto")  # auto, gemini, google, marian
    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "auto")  # auto, gtts, edge, piper
    SEPARATION_PROVIDER: str = os.getenv("SEPARATION_PROVIDER", "auto")  # auto, demucs, spectral_filter
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # SQLite Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'database.sqlite'}")

settings = Settings()

# Ensure directories exist
for folder in [
    settings.UPLOAD_DIR,
    settings.EXTRACTED_AUDIO_DIR,
    settings.VOCALS_DIR,
    settings.BACKGROUND_AUDIO_DIR,
    settings.TRANSCRIPTS_DIR,
    settings.TRANSLATIONS_DIR,
    settings.GENERATED_VOICE_DIR,
    settings.FINAL_VIDEOS_DIR,
    settings.TEMP_DIR,
    settings.OUTPUT_DIR,
    settings.MODELS_DIR,
]:
    folder.mkdir(parents=True, exist_ok=True)
