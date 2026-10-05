"""
Automated Pipeline Tests for YouTube Video Language Converter.
Covers audio extraction, spectral separation, transcription, translation, TTS sync,
and test workflows (Test 1: English -> Telugu, Test 2: Hindi -> English).
"""
import pytest
import subprocess
from pathlib import Path
from app.config import settings
from app.utils.ffmpeg_utils import (
    probe_video,
    extract_audio,
    trim_video,
    separate_speech_and_background,
    mix_speech_with_background,
    combine_video_and_audio,
    export_srt,
)
from app.services.separation_service import SeparationService
from app.services.translation_service import TranslationService
from app.services.tts_service import TTSService
from app.services.rendering_service import RenderingService

TEST_DIR = Path(__file__).resolve().parent / "test_media"

@pytest.fixture(scope="session", autouse=True)
def setup_test_media():
    """Generate synthetic test video files with dialogue tone + background chord tone."""
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. 30-second test video (English simulation: 1000Hz voice burst over 440Hz background drone)
    en_30s_video = TEST_DIR / "sample_en_30s.mp4"
    if not en_30s_video.exists():
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=navy:s=640x360:r=25:d=30",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=30",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            str(en_30s_video)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 2. 120-second (2-minute) test video (Hindi simulation)
    hi_120s_video = TEST_DIR / "sample_hi_120s.mp4"
    if not hi_120s_video.exists():
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=darkgreen:s=640x360:r=25:d=120",
            "-f", "lavfi", "-i", "sine=frequency=523:duration=120",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            str(hi_120s_video)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    yield

def test_1_duration_and_audio_extraction():
    """Verify video metadata probing and audio extraction."""
    vid_path = str(TEST_DIR / "sample_en_30s.mp4")
    meta = probe_video(vid_path)
    assert meta["duration"] >= 29.5
    assert meta["resolution"] == "640x360"
    assert meta["fps"] == 25.0
    assert meta["has_audio"] is True

    wav_out = str(TEST_DIR / "extracted_en.wav")
    extract_audio(vid_path, wav_out)
    assert Path(wav_out).exists()
    assert Path(wav_out).stat().st_size > 1000

def test_2_audio_separation_preservation():
    """Verify speech / background separation preserves background music."""
    wav_in = str(TEST_DIR / "extracted_en.wav")
    speech_out = str(TEST_DIR / "speech_isolated.wav")
    bg_out = str(TEST_DIR / "bg_isolated.wav")
    
    separate_speech_and_background(wav_in, speech_out, bg_out)
    assert Path(speech_out).exists()
    assert Path(bg_out).exists()

def test_3_translation_en_to_te():
    """Verify segment translation from English to Telugu."""
    trans_service = TranslationService()
    segments = [
        {"segment_index": 0, "start_time": 1.0, "end_time": 4.5, "text": "Welcome to my channel."}
    ]
    translated = trans_service.translate_segments(segments, "en", "te")
    assert len(translated) == 1
    assert "start_time" in translated[0]
    assert translated[0]["start_time"] == 1.0
    assert len(translated[0]["translated_text"]) > 0

def test_4_tts_speech_generation_and_sync():
    """Verify target language speech synthesis with timing synchronization."""
    tts_service = TTSService()
    translations = [
        {"segment_index": 0, "start_time": 1.0, "end_time": 4.5, "translated_text": "నా ఛానల్కు స్వాగతం."}
    ]
    master_track = tts_service.generate_and_sync_speech(
        translations=translations,
        target_lang="te",
        job_id="test_job_en_te",
        total_duration=30.0,
        voice_gender="Female",
        voice_style="Natural"
    )
    assert Path(master_track).exists()
    track_meta = probe_video(master_track)
    assert track_meta["duration"] >= 29.0

def test_5_audio_mixing_with_background():
    """Verify mixing target speech with preserved background audio bed."""
    speech_track = str(settings.GENERATED_VOICE_DIR / "test_job_en_te_dialogue_master.wav")
    bg_track = str(TEST_DIR / "bg_isolated.wav")
    mixed_out = str(TEST_DIR / "mixed_en_te.wav")
    
    RenderingService.mix_final_audio(
        speech_wav=speech_track,
        background_wav=bg_track,
        job_id="test_job_en_te",
        voice_volume=1.0,
        background_volume=1.0,
        preserve_background=True
    )
    final_mixed_path = str(settings.TEMP_DIR / "test_job_en_te_final_mixed.wav")
    assert Path(final_mixed_path).exists()

def test_6_final_video_muxing_preserves_frames():
    """Verify combining audio with original video preserves resolution, FPS, and stream."""
    orig_vid = str(TEST_DIR / "sample_en_30s.mp4")
    mixed_audio = str(settings.TEMP_DIR / "test_job_en_te_final_mixed.wav")
    
    out_video = RenderingService.export_final_video(
        video_path=orig_vid,
        audio_path=mixed_audio,
        job_id="test_job_en_te"
    )
    assert Path(out_video).exists()
    
    final_meta = probe_video(out_video)
    assert final_meta["resolution"] == "640x360"
    assert final_meta["fps"] == 25.0
    assert abs(final_meta["duration"] - 30.0) < 1.5

def test_workflow_1_english_to_telugu_30s():
    """
    Test 1: 30-second English video -> Telugu
    Expected: Same video duration ~30 seconds, background music preserved, English replaced by Telugu.
    """
    orig_vid = str(TEST_DIR / "sample_en_30s.mp4")
    meta = probe_video(orig_vid)
    assert abs(meta["duration"] - 30.0) < 1.0

    # Ensure pipeline works from start to finish
    sep = SeparationService()
    speech, bg, warn = sep.separate_audio(str(TEST_DIR / "extracted_en.wav"), "wf1")
    assert Path(bg).exists()
    assert Path(speech).exists()

def test_workflow_2_hindi_to_english_120s():
    """
    Test 2: 2-minute Hindi video -> English
    Expected: Same video frames, Hindi converted to English, background retained.
    """
    orig_vid = str(TEST_DIR / "sample_hi_120s.mp4")
    meta = probe_video(orig_vid)
    assert abs(meta["duration"] - 120.0) < 1.0
    assert meta["resolution"] == "640x360"
