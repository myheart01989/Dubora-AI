"""
Translation service supporting all required target languages.
Includes Gemini AI translation and Google Translate interfaces.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os
import json
import urllib.parse
import urllib.request
import requests

from app.config import settings

LANGUAGE_NAME_MAP = {
    "en": "English",
    "te": "Telugu",
    "hi": "Hindi",
    "ta": "Tamil",
    "kn": "Kannada",
    "ml": "Malayalam",
    "mr": "Marathi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "ur": "Urdu",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ar": "Arabic",
    "ru": "Russian",
}

class TranslationProvider(ABC):
    @abstractmethod
    def translate_segments(
        self,
        segments: List[Dict[str, Any]],
        source_lang: str,
        target_lang: str
    ) -> List[Dict[str, Any]]:
        pass

class GeminiTranslationProvider(TranslationProvider):
    def translate_segments(
        self,
        segments: List[Dict[str, Any]],
        source_lang: str,
        target_lang: str
    ) -> List[Dict[str, Any]]:
        api_key = os.getenv("GEMINI_API_KEY", settings.GEMINI_API_KEY)
        if not api_key:
            raise ValueError("GEMINI_API_KEY missing.")

        from google import genai

        client = genai.Client(api_key=api_key)
        target_name = LANGUAGE_NAME_MAP.get(target_lang, target_lang)
        source_name = LANGUAGE_NAME_MAP.get(source_lang, "Original Language")

        input_payload = [
            {"index": seg["segment_index"], "text": seg["text"]}
            for seg in segments
        ]

        prompt = (
            f"You are a professional film/video dubbing translator. Translate the following dialogue segments from {source_name} into {target_name}.\n"
            "Critical requirements:\n"
            "1. Preserve natural spoken dialogue cadence suitable for dubbing.\n"
            "2. Keep the phrasing concise so it matches the speaker's original timing.\n"
            "3. Return a strictly valid JSON array of objects with keys 'index' and 'translated_text'.\n"
            f"Input:\n{json.dumps(input_payload, ensure_ascii=False)}"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        text = response.text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        parsed = json.loads(text)
        trans_map = {item["index"]: item["translated_text"] for item in parsed}

        results = []
        for seg in segments:
            idx = seg["segment_index"]
            results.append({
                "segment_index": idx,
                "start_time": seg["start_time"],
                "end_time": seg["end_time"],
                "original_text": seg["text"],
                "translated_text": trans_map.get(idx, seg["text"]),
            })
        return results

class WebGoogleTranslateProvider(TranslationProvider):
    """Zero-key Google Translate web endpoint provider."""
    def translate_segments(
        self,
        segments: List[Dict[str, Any]],
        source_lang: str,
        target_lang: str
    ) -> List[Dict[str, Any]]:
        results = []
        s_lang = "auto" if source_lang == "auto" else source_lang
        t_lang = target_lang

        for seg in segments:
            text = seg.get("text", "")
            if not text.strip():
                results.append({
                    "segment_index": seg["segment_index"],
                    "start_time": seg["start_time"],
                    "end_time": seg["end_time"],
                    "original_text": text,
                    "translated_text": "",
                })
                continue
                
            try:
                url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={s_lang}&tl={t_lang}&dt=t&q={urllib.parse.quote(text)}"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    translated = "".join([part[0] for part in data[0] if part and part[0]])
            except Exception:
                translated = text  # fallback to original if network glitch

            results.append({
                "segment_index": seg["segment_index"],
                "start_time": seg["start_time"],
                "end_time": seg["end_time"],
                "original_text": text,
                "translated_text": translated,
            })
        return results

class TranslationService:
    def __init__(self):
        self.gemini_provider = GeminiTranslationProvider()
        self.web_provider = WebGoogleTranslateProvider()

    def translate_segments(
        self,
        segments: List[Dict[str, Any]],
        source_lang: str,
        target_lang: str
    ) -> List[Dict[str, Any]]:
        """
        Translate list of dialogue segments.
        Prefers Gemini for natural conversational dubbing when API key is provided,
        otherwise uses Google Translate client.
        """
        if os.getenv("GEMINI_API_KEY", settings.GEMINI_API_KEY):
            try:
                return self.gemini_provider.translate_segments(segments, source_lang, target_lang)
            except Exception as e:
                print(f"[TranslationService] Gemini fallback: {e}")

        return self.web_provider.translate_segments(segments, source_lang, target_lang)
