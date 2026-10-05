"""
API Endpoint Integration Tests using FastAPI TestClient.
"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import io

from app.main import app
from app.database import init_db

client = TestClient(app)

@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    init_db()

def test_languages_endpoint():
    res = client.get("/api/languages")
    assert res.status_code == 200
    data = res.json()
    assert "languages" in data
    codes = [l["code"] for l in data["languages"]]
    assert "en" in codes
    assert "te" in codes
    assert "hi" in codes

def test_voices_endpoint():
    res = client.get("/api/voices")
    assert res.status_code == 200
    data = res.json()
    assert "genders" in data
    assert "Female" in data["genders"]
    assert "Male" in data["genders"]

def test_language_validation_identical():
    # Attempting to convert en -> en should fail validation
    payload = {
        "video_id": "non-existent-id",
        "original_language": "en",
        "target_language": "en"
    }
    res = client.post("/api/process", json=payload)
    assert res.status_code in [400, 404]

def test_video_upload_and_inspect():
    # Upload synthetic mp4 from test_media if exists
    test_media = Path(__file__).resolve().parent / "test_media" / "sample_en_30s.mp4"
    if not test_media.exists():
        pytest.skip("Test media not yet generated")

    with open(test_media, "rb") as f:
        res = client.post(
            "/api/video/upload",
            files={"file": ("sample_en_30s.mp4", f, "video/mp4")}
        )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    video = data["video"]
    assert video["resolution"] == "640x360"
    assert video["duration"] >= 29.0
