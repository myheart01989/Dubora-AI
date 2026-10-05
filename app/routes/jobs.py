"""
Job processing routes and pipeline execution.
Tracks progress through all 11 stages and manages downloadable artifacts.
"""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, SessionLocal
from app.models.models import Video, ProcessingJob, Transcript, Translation, AudioTrack, OutputFile
from app.utils.validators import validate_languages, parse_time_to_seconds
from app.utils.ffmpeg_utils import probe_video
from app.services.video_service import VideoService
from app.services.audio_service import AudioService
from app.services.separation_service import SeparationService
from app.services.transcription_service import TranscriptionService
from app.services.translation_service import TranslationService
from app.services.tts_service import TTSService
from app.services.rendering_service import RenderingService

router = APIRouter(prefix="/api", tags=["jobs"])

class ProcessRequest(BaseModel):
    video_id: str
    original_language: str = "auto"
    target_language: str = "te"  # default Telugu
    max_duration: int = 600       # seconds (0 for full video)
    trim_start: float = 0.0
    trim_end: Optional[float] = None
    auto_trim_if_exceeded: bool = True
    
    # Audio Settings
    preserve_background_music: bool = True
    preserve_sound_effects: bool = True
    replace_spoken_language: bool = True
    preserve_original_video: bool = True
    voice_volume: float = 1.0           # 0.0 to 2.0
    background_music_volume: float = 1.0 # 0.0 to 2.0
    sound_effects_volume: float = 1.0   # 0.0 to 2.0
    mute_original_speech: bool = True
    
    # Target Voice Settings
    voice_gender: str = "Female"
    voice_style: str = "Natural"
    speaking_speed: float = 1.0
    voice_pitch: str = "Normal"
    
    # Subtitle Settings
    generate_original_subtitles: bool = True
    generate_target_subtitles: bool = True
    burn_subtitles: bool = False
    subtitle_position: str = "Bottom"
    subtitle_size: str = "Medium"

def run_conversion_pipeline(job_id: str):
    """Background worker executing the 11-step pipeline."""
    db = SessionLocal()
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            return
            
        video = db.query(Video).filter(Video.id == job.video_id).first()
        if not video:
            job.status = "FAILED"
            job.error_message = "Associated video file not found."
            db.commit()
            return

        def update_progress(stage: int, progress: int, message: str):
            job.current_stage = stage
            job.progress = progress
            job.stage_message = message
            db.commit()

        job.status = "PROCESSING"
        db.commit()

        # STAGE 2: Analyzing Video & Enforcing Duration
        update_progress(2, 10, "Analyzing video stream and duration...")
        meta = probe_video(video.storage_path)
        actual_dur = meta["duration"]

        if job.max_duration > 0 and actual_dur > job.max_duration and not job.auto_trim_applied:
            job.status = "FAILED"
            job.error_message = f"Video duration ({actual_dur:.1f}s) exceeds the selected limit of {job.max_duration}s."
            db.commit()
            return

        # Apply trimming if requested or duration limit active
        duration_info = VideoService.enforce_duration_limit(
            video_path=video.storage_path,
            max_duration=job.max_duration,
            trim_start=job.trim_start,
            trim_end=job.trim_end
        )
        working_video_path = duration_info["path"]
        active_duration = duration_info["duration"]

        # STAGE 3: Extracting Audio
        update_progress(3, 20, "Extracting audio track from video...")
        audio_service = AudioService()
        extracted_audio_path = audio_service.extract_audio_from_video(working_video_path, job.id)
        job.original_audio_path = extracted_audio_path
        db.commit()

        # Save audio track record
        db.add(AudioTrack(job_id=job.id, track_type="extracted", file_path=extracted_audio_path, duration=active_duration))
        db.commit()

        # STAGE 4: Separating Speech from Background Music & SFX
        update_progress(4, 30, "Separating voice from background music & sound effects...")
        sep_service = SeparationService()
        speech_wav, bg_wav, sep_warning = sep_service.separate_audio(extracted_audio_path, job.id)
        job.warning_message = sep_warning
        db.add(AudioTrack(job_id=job.id, track_type="vocals", file_path=speech_wav, duration=active_duration))
        db.add(AudioTrack(job_id=job.id, track_type="background", file_path=bg_wav, duration=active_duration))
        db.commit()

        # STAGE 5: Transcribing Speech
        update_progress(5, 45, f"Transcribing dialogue ({job.original_language})...")
        trans_service = TranscriptionService()
        raw_segments = trans_service.transcribe_audio(speech_wav, job.original_language)

        # Persist transcripts
        for seg in raw_segments:
            t_rec = Transcript(
                job_id=job.id,
                segment_index=seg["segment_index"],
                start_time=seg["start_time"],
                end_time=seg["end_time"],
                text=seg["text"]
            )
            db.add(t_rec)
        db.commit()

        # STAGE 6: Translating
        update_progress(6, 60, f"Translating dialogue into {job.target_language}...")
        translation_service = TranslationService()
        translated_segments = translation_service.translate_segments(
            raw_segments,
            job.original_language,
            job.target_language
        )

        for trans in translated_segments:
            db.add(Translation(
                job_id=job.id,
                segment_index=trans["segment_index"],
                start_time=trans["start_time"],
                end_time=trans["end_time"],
                original_text=trans["original_text"],
                translated_text=trans["translated_text"]
            ))
        db.commit()

        # STAGE 7 & 8: Generating Voice & Synchronizing Audio
        update_progress(7, 75, f"Synthesizing {job.target_language} speech ({job.voice_gender} / {job.voice_style})...")
        tts_service = TTSService()
        speech_track_wav = tts_service.generate_and_sync_speech(
            translations=translated_segments,
            target_lang=job.target_language,
            job_id=job.id,
            total_duration=active_duration,
            voice_gender=job.voice_gender,
            voice_style=job.voice_style,
            speaking_speed=job.speaking_speed,
            voice_pitch=job.voice_pitch
        )
        db.add(AudioTrack(job_id=job.id, track_type="generated", file_path=speech_track_wav, duration=active_duration))
        db.commit()

        update_progress(8, 85, "Synchronizing dialogue timing with video frames...")

        # STAGE 9: Mixing Audio (Target Speech + Preserved Background Music + SFX)
        update_progress(9, 90, "Mixing target speech with original background music & sound effects...")
        rendering_service = RenderingService()
        final_mixed_wav = rendering_service.mix_final_audio(
            speech_wav=speech_track_wav,
            background_wav=bg_wav,
            job_id=job.id,
            voice_volume=job.voice_volume,
            background_volume=job.background_music_volume,
            preserve_background=job.preserve_background_music
        )
        job.translated_audio_path = final_mixed_wav
        db.add(AudioTrack(job_id=job.id, track_type="mixed", file_path=final_mixed_wav, duration=active_duration))
        db.commit()

        # Generate Subtitle Artifacts
        subtitles_dict = rendering_service.generate_subtitles(raw_segments, translated_segments, job.id)
        job.output_srt_path = subtitles_dict["srt"]
        job.output_vtt_path = subtitles_dict["vtt"]
        job.original_transcript_path = subtitles_dict["original_txt"]
        job.translated_transcript_path = subtitles_dict["translated_txt"]
        db.commit()

        # STAGE 10: Rendering Final Video (preserving video stream untouched)
        update_progress(10, 95, "Muxing final audio with original video frames...")
        final_video_path = rendering_service.export_final_video(
            video_path=working_video_path,
            audio_path=final_mixed_wav,
            job_id=job.id,
            burn_subtitles=job.burn_subtitles,
            srt_path=subtitles_dict["srt"],
            subtitle_position=job.subtitle_position,
            subtitle_size=job.subtitle_size
        )
        job.output_video_path = final_video_path
        db.commit()

        # Register downloadable files
        vid_p = Path(final_video_path)
        db.add(OutputFile(
            id=str(uuid.uuid4()),
            job_id=job.id,
            file_type="video",
            file_path=final_video_path,
            file_size=vid_p.stat().st_size if vid_p.exists() else 0,
            download_filename=f"{Path(video.original_name).stem}_{job.target_language}.mp4"
        ))

        srt_p = Path(subtitles_dict["srt"])
        db.add(OutputFile(
            id=str(uuid.uuid4()),
            job_id=job.id,
            file_type="srt",
            file_path=subtitles_dict["srt"],
            file_size=srt_p.stat().st_size if srt_p.exists() else 0,
            download_filename=f"{Path(video.original_name).stem}_{job.target_language}.srt"
        ))

        vtt_p = Path(subtitles_dict["vtt"])
        db.add(OutputFile(
            id=str(uuid.uuid4()),
            job_id=job.id,
            file_type="vtt",
            file_path=subtitles_dict["vtt"],
            file_size=vtt_p.stat().st_size if vtt_p.exists() else 0,
            download_filename=f"{Path(video.original_name).stem}_{job.target_language}.vtt"
        ))

        orig_t_p = Path(subtitles_dict["original_txt"])
        db.add(OutputFile(
            id=str(uuid.uuid4()),
            job_id=job.id,
            file_type="original_txt",
            file_path=subtitles_dict["original_txt"],
            file_size=orig_t_p.stat().st_size if orig_t_p.exists() else 0,
            download_filename=f"{Path(video.original_name).stem}_original_transcript.txt"
        ))

        trans_t_p = Path(subtitles_dict["translated_txt"])
        db.add(OutputFile(
            id=str(uuid.uuid4()),
            job_id=job.id,
            file_type="translated_txt",
            file_path=subtitles_dict["translated_txt"],
            file_size=trans_t_p.stat().st_size if trans_t_p.exists() else 0,
            download_filename=f"{Path(video.original_name).stem}_{job.target_language}_transcript.txt"
        ))

        # STAGE 11: Completed
        job.status = "COMPLETED"
        job.completed_at = datetime.utcnow()
        update_progress(11, 100, "Conversion completed successfully!")

    except Exception as e:
        db.rollback()
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if job:
            job.status = "FAILED"
            job.error_message = f"Processing error: {str(e)}"
            db.commit()
    finally:
        db.close()

@router.post("/process")
async def start_processing(
    req: ProcessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start video language conversion workflow."""
    video = db.query(Video).filter(Video.id == req.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")

    # Validate languages
    valid, err = validate_languages(req.original_language, req.target_language)
    if not valid:
        raise HTTPException(status_code=400, detail=err)

    # Validate duration limits
    if req.max_duration > 0 and video.duration > req.max_duration:
        if not req.auto_trim_if_exceeded:
            raise HTTPException(
                status_code=400,
                detail=f"Video exceeds the selected duration limit of {req.max_duration} seconds (video is {video.duration:.1f}s)."
            )

    job_id = str(uuid.uuid4())
    job = ProcessingJob(
        id=job_id,
        video_id=video.id,
        status="QUEUED",
        current_stage=1,
        progress=5,
        stage_message="Job queued for processing...",
        original_language=req.original_language,
        target_language=req.target_language,
        max_duration=req.max_duration,
        trim_start=req.trim_start,
        trim_end=req.trim_end,
        auto_trim_applied=req.auto_trim_if_exceeded,
        preserve_background_music=req.preserve_background_music,
        preserve_sound_effects=req.preserve_sound_effects,
        replace_spoken_language=req.replace_spoken_language,
        preserve_original_video=req.preserve_original_video,
        voice_volume=req.voice_volume,
        background_music_volume=req.background_music_volume,
        sound_effects_volume=req.sound_effects_volume,
        mute_original_speech=req.mute_original_speech,
        voice_gender=req.voice_gender,
        voice_style=req.voice_style,
        speaking_speed=req.speaking_speed,
        voice_pitch=req.voice_pitch,
        generate_original_subtitles=req.generate_original_subtitles,
        generate_target_subtitles=req.generate_target_subtitles,
        burn_subtitles=req.burn_subtitles,
        subtitle_position=req.subtitle_position,
        subtitle_size=req.subtitle_size,
    )
    db.add(job)
    db.commit()

    background_tasks.add_task(run_conversion_pipeline, job_id)

    return {
        "status": "success",
        "job_id": job_id,
        "message": "Processing started"
    }

@router.get("/job/{job_id}")
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Poll job progress and fetch results."""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    output_files = db.query(OutputFile).filter(OutputFile.job_id == job_id).all()
    transcripts = db.query(Transcript).filter(Transcript.job_id == job_id).order_by(Transcript.segment_index).all()
    translations = db.query(Translation).filter(Translation.job_id == job_id).order_by(Translation.segment_index).all()

    return {
        "id": job.id,
        "video_id": job.video_id,
        "status": job.status,
        "current_stage": job.current_stage,
        "progress": job.progress,
        "stage_message": job.stage_message,
        "original_language": job.original_language,
        "target_language": job.target_language,
        "warning_message": job.warning_message,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "has_outputs": job.status == "COMPLETED",
        "output_files": [
            {
                "id": f.id,
                "file_type": f.file_type,
                "file_size": f.file_size,
                "filename": f.download_filename,
            }
            for f in output_files
        ],
        "dialogue_segments": [
            {
                "index": tr.segment_index,
                "start_time": tr.start_time,
                "end_time": tr.end_time,
                "original_text": tr.original_text,
                "translated_text": tr.translated_text,
            }
            for tr in translations
        ]
    }

@router.get("/download/{file_id}")
async def download_file(file_id: str, db: Session = Depends(get_db)):
    """Download output artifacts."""
    out_file = db.query(OutputFile).filter(OutputFile.id == file_id).first()
    if not out_file:
        raise HTTPException(status_code=404, detail="File record not found")

    path = Path(out_file.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File on disk not found")

    media_type = "video/mp4" if out_file.file_type == "video" else "text/plain"
    if out_file.file_type in ["srt", "vtt"]:
        media_type = "text/vtt" if out_file.file_type == "vtt" else "application/x-subrip"

    return FileResponse(
        path=str(path),
        filename=out_file.download_filename,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{out_file.download_filename}"'}
    )

@router.get("/media/{job_id}/{media_type}")
async def stream_media(job_id: str, media_type: str, db: Session = Depends(get_db)):
    """Stream media files for browser video and audio comparison preview."""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    file_path = None
    content_type = "video/mp4"

    if media_type == "original_video":
        video = db.query(Video).filter(Video.id == job.video_id).first()
        if video and Path(video.storage_path).exists():
            file_path = video.storage_path
            content_type = "video/mp4"
    elif media_type == "target_video":
        if job.output_video_path and Path(job.output_video_path).exists():
            file_path = job.output_video_path
            content_type = "video/mp4"
    elif media_type == "original_audio":
        if job.original_audio_path and Path(job.original_audio_path).exists():
            file_path = job.original_audio_path
            content_type = "audio/wav"
    elif media_type == "translated_audio":
        if job.translated_audio_path and Path(job.translated_audio_path).exists():
            file_path = job.translated_audio_path
            content_type = "audio/wav"

    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail=f"Media {media_type} not available")

    return FileResponse(path=file_path, media_type=content_type)
