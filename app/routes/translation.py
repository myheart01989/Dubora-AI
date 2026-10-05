"""
Translation and voice metadata endpoints.
"""
from fastapi import APIRouter
from app.utils.validators import SUPPORTED_LANGUAGES

router = APIRouter(prefix="/api", tags=["languages_and_voices"])

@router.get("/languages")
async def get_languages():
    """Return supported languages for original and target conversion."""
    return {
        "languages": SUPPORTED_LANGUAGES
    }

@router.get("/voices")
async def get_voices():
    """Return available voice customization parameters."""
    return {
        "genders": ["Female", "Male", "Neutral"],
        "styles": ["Natural", "Professional", "Friendly", "Narrator", "Energetic", "Calm"],
        "speeds": [0.75, 1.0, 1.25, 1.5],
        "pitches": ["Low", "Normal", "High"]
    }
