"""
DukaanSaathi — Gnani Timbre TTS Service (Phase 4 Task 7 & 9)
Reuses the verified Phase 1 Timbre v2.5 live adapter, headers, audio caching,
and graceful fallback handling.
"""

import base64
import io
import json
import logging
import struct
import time
import uuid
import wave
from typing import Dict, Optional, Tuple
from pydantic import BaseModel
import requests

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class TTSResult(BaseModel):
    success: bool
    audio_bytes: Optional[bytes] = None
    audio_format: str = "audio/wav"
    latency_ms: float = 0.0
    audio_id: Optional[str] = None
    error_message: Optional[str] = None


class TimbreTTSService:
    # Class-level shared in-memory audio cache: audio_id -> (audio_bytes, timestamp)
    _audio_cache: Dict[str, Tuple[bytes, float]] = {}
    _MAX_CACHE_ITEMS = 500

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        default_voice: str = "Nalini",
        default_language: str = "hi-IN",
        timeout_seconds: int = 25,
        force_mock: bool = False
    ):
        self.api_key = settings.GNANI_API_KEY if api_key is None else api_key
        self.endpoint_url = endpoint_url or settings.GNANI_TIMBRE_ENDPOINT
        self.default_voice = default_voice
        self.default_language = default_language
        self.timeout_seconds = timeout_seconds
        self.force_mock = force_mock

    @classmethod
    def get_cached_audio(cls, audio_id: str) -> Optional[bytes]:
        """Retrieves cached synthesized audio bytes by audio_id."""
        entry = cls._audio_cache.get(audio_id)
        if entry:
            return entry[0]
        return None

    @classmethod
    def store_in_cache(cls, audio_bytes: bytes) -> str:
        """Stores audio bytes in the cache and returns a unique audio_id."""
        if len(cls._audio_cache) >= cls._MAX_CACHE_ITEMS:
            # Evict oldest 50 items
            sorted_keys = sorted(cls._audio_cache.keys(), key=lambda k: cls._audio_cache[k][1])
            for k in sorted_keys[:50]:
                cls._audio_cache.pop(k, None)

        audio_id = f"aud_{uuid.uuid4().hex[:12]}"
        cls._audio_cache[audio_id] = (audio_bytes, time.time())
        return audio_id

    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        language: Optional[str] = None
    ) -> TTSResult:
        """
        Synthesizes spoken text into playable 16kHz linear PCM WAV using Gnani Timbre.
        """
        start_time = time.time()
        target_voice = voice or self.default_voice
        target_lang = language or self.default_language

        clean_text = text.strip()
        if not clean_text:
            return TTSResult(
                success=False,
                error_message="Cannot synthesize audio from empty text."
            )

        # Handle Mock Mode
        if self.force_mock or self.api_key == "mock":
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                # 0.5s silence
                wf.writeframes(struct.pack("<h", 0) * 8000)
            mock_audio = buf.getvalue()
            audio_id = self.store_in_cache(mock_audio)
            latency = (time.time() - start_time) * 1000

            return TTSResult(
                success=True,
                audio_bytes=mock_audio,
                audio_format="audio/wav",
                latency_ms=round(latency, 2),
                audio_id=audio_id
            )

        if not self.api_key:
            return TTSResult(
                success=False,
                error_message="GNANI_API_KEY is not configured on the backend."
            )

        headers = {
            "X-API-Key-ID": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36 DukaanSaathi/1.0"
            )
        }

        payload = {
            "text": clean_text,
            "voice": target_voice,
            "model": "timbre-v2.5",
            "language": target_lang,
            "audio_config": {
                "sample_rate": 16000,
                "encoding": "linear_pcm",
                "container": "wav"
            }
        }

        try:
            resp = requests.post(
                self.endpoint_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=self.timeout_seconds
            )
            roundtrip_ms = (time.time() - start_time) * 1000

            if resp.status_code == 200:
                raw_data = resp.content
                audio_bytes = None

                # Check if binary WAV audio returned directly
                if raw_data.startswith(b"RIFF") or "audio" in resp.headers.get("Content-Type", ""):
                    audio_bytes = raw_data
                else:
                    # Check if JSON containing base64 audio
                    try:
                        data = resp.json()
                        b64 = (
                            data.get("audio_content") or
                            data.get("audio") or
                            data.get("data")
                        )
                        if b64:
                            audio_bytes = base64.b64decode(b64)
                    except Exception as parse_err:
                        logger.warning(f"Could not parse Timbre JSON response: {parse_err}")

                if audio_bytes and len(audio_bytes) > 44:
                    audio_id = self.store_in_cache(audio_bytes)
                    return TTSResult(
                        success=True,
                        audio_bytes=audio_bytes,
                        audio_format="audio/wav",
                        latency_ms=round(roundtrip_ms, 2),
                        audio_id=audio_id
                    )
                else:
                    err_msg = "Timbre returned empty or invalid audio payload."
                    logger.error(err_msg)
                    return TTSResult(
                        success=False,
                        latency_ms=round(roundtrip_ms, 2),
                        error_message=err_msg
                    )
            else:
                err_msg = f"Timbre HTTP {resp.status_code}: {resp.text[:200]}"
                logger.error(err_msg)
                return TTSResult(
                    success=False,
                    latency_ms=round(roundtrip_ms, 2),
                    error_message=err_msg
                )

        except requests.Timeout:
            latency = (time.time() - start_time) * 1000
            err_msg = f"Timbre TTS request timed out after {self.timeout_seconds}s"
            logger.error(err_msg)
            return TTSResult(
                success=False,
                latency_ms=round(latency, 2),
                error_message=err_msg
            )
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            err_msg = f"Timbre TTS connection failed: {e}"
            logger.error(err_msg)
            return TTSResult(
                success=False,
                latency_ms=round(latency, 2),
                error_message=err_msg
            )
