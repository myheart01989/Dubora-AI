"""
SQLAlchemy ORM models for YouTube Video Language Converter.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Video(Base):
    __tablename__ = "videos"
    
    id = Column(String(36), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    duration = Column(Float, default=0.0)  # in seconds
    fps = Column(Float, default=0.0)
    resolution = Column(String(50), default="unknown")
    audio_codec = Column(String(50), default="aac")
    video_codec = Column(String(50), default="h264")
    sample_rate = Column(Integer, default=44100)
    channels = Column(Integer, default=2)
    file_size = Column(Integer, default=0)  # bytes
    storage_path = Column(String(1024), nullable=False)
    source_type = Column(String(50), default="upload")  # 'upload' or 'youtube'
    youtube_url = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    jobs = relationship("ProcessingJob", back_populates="video", cascade="all, delete-orphan")

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    
    id = Column(String(36), primary_key=True, index=True)
    video_id = Column(String(36), ForeignKey("videos.id"), nullable=False)
    status = Column(String(50), default="QUEUED")  # QUEUED, PROCESSING, COMPLETED, FAILED
    current_stage = Column(Integer, default=1)  # 1 to 11
    progress = Column(Integer, default=0)  # 0 to 100
    stage_message = Column(String(255), default="Initializing...")
    
    # Language Conversion
    original_language = Column(String(50), default="auto")
    target_language = Column(String(50), nullable=False)
    
    # Video Duration Settings
    max_duration = Column(Integer, default=600)  # in seconds
    trim_start = Column(Float, default=0.0)
    trim_end = Column(Float, nullable=True)
    auto_trim_applied = Column(Boolean, default=False)
    
    # Audio Preservation Settings
    preserve_background_music = Column(Boolean, default=True)
    preserve_sound_effects = Column(Boolean, default=True)
    replace_spoken_language = Column(Boolean, default=True)
    preserve_original_video = Column(Boolean, default=True)
    voice_volume = Column(Float, default=1.0)  # 0.0 - 2.0 (0-200%)
    background_music_volume = Column(Float, default=1.0)  # 0.0 - 2.0
    sound_effects_volume = Column(Float, default=1.0)  # 0.0 - 2.0
    mute_original_speech = Column(Boolean, default=True)
    
    # Target Voice Settings
    voice_gender = Column(String(50), default="Female")
    voice_style = Column(String(50), default="Natural")
    speaking_speed = Column(Float, default=1.0)
    voice_pitch = Column(String(50), default="Normal")
    
    # Subtitle Settings
    generate_original_subtitles = Column(Boolean, default=True)
    generate_target_subtitles = Column(Boolean, default=True)
    burn_subtitles = Column(Boolean, default=False)
    subtitle_position = Column(String(50), default="Bottom")
    subtitle_size = Column(String(50), default="Medium")
    
    # Output file paths
    output_video_path = Column(String(1024), nullable=True)
    output_srt_path = Column(String(1024), nullable=True)
    output_vtt_path = Column(String(1024), nullable=True)
    original_transcript_path = Column(String(1024), nullable=True)
    translated_transcript_path = Column(String(1024), nullable=True)
    original_audio_path = Column(String(1024), nullable=True)
    translated_audio_path = Column(String(1024), nullable=True)
    
    error_message = Column(Text, nullable=True)
    warning_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    video = relationship("Video", back_populates="jobs")
    transcripts = relationship("Transcript", back_populates="job", cascade="all, delete-orphan")
    translations = relationship("Translation", back_populates="job", cascade="all, delete-orphan")
    audio_tracks = relationship("AudioTrack", back_populates="job", cascade="all, delete-orphan")
    output_files = relationship("OutputFile", back_populates="job", cascade="all, delete-orphan")

class Transcript(Base):
    __tablename__ = "transcripts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey("processing_jobs.id"), nullable=False)
    segment_index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)  # in seconds
    end_time = Column(Float, nullable=False)    # in seconds
    text = Column(Text, nullable=False)
    
    job = relationship("ProcessingJob", back_populates="transcripts")

class Translation(Base):
    __tablename__ = "translations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey("processing_jobs.id"), nullable=False)
    segment_index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    original_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=False)
    
    job = relationship("ProcessingJob", back_populates="translations")

class AudioTrack(Base):
    __tablename__ = "audio_tracks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey("processing_jobs.id"), nullable=False)
    track_type = Column(String(50), nullable=False)  # 'extracted', 'vocals', 'background', 'generated', 'mixed'
    file_path = Column(String(1024), nullable=False)
    duration = Column(Float, default=0.0)
    
    job = relationship("ProcessingJob", back_populates="audio_tracks")

class OutputFile(Base):
    __tablename__ = "output_files"
    
    id = Column(String(36), primary_key=True, index=True)
    job_id = Column(String(36), ForeignKey("processing_jobs.id"), nullable=False)
    file_type = Column(String(50), nullable=False)  # 'video', 'srt', 'vtt', 'original_txt', 'translated_txt', 'original_audio', 'translated_audio'
    file_path = Column(String(1024), nullable=False)
    file_size = Column(Integer, default=0)
    download_filename = Column(String(255), nullable=False)
    
    job = relationship("ProcessingJob", back_populates="output_files")
