"""
DukaanSaathi — Gnani Prisma STT Service (Phase 4 Task 3)
Reuses the verified Phase 1 Prisma v3 live adapter, headers, and code-mixed transcription.
"""

import logging
import time
from typing import Optional
from pydantic import BaseModel
import requests

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class STTResult(BaseModel):
    success: bool
    transcript: str = ""
    detected_language: str = "hi-IN"
    processing_time_ms: float = 0.0
    latency_ms: float = 0.0
    request_id: Optional[str] = None
    error_message: Optional[str] = None


class PrismaSTTService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        timeout_seconds: int = 25,
        force_mock: bool = False
    ):
        self.api_key = settings.GNANI_API_KEY if api_key is None else api_key
        self.endpoint_url = endpoint_url or settings.GNANI_PRISMA_ENDPOINT
        self.timeout_seconds = timeout_seconds
        self.force_mock = force_mock

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language_code: str = "indic-auto",
        format_mode: str = "codemix"
    ) -> STTResult:
        """
        Submits audio payload to Gnani Prisma STT endpoint and returns normalized STTResult.
        """
        start_time = time.time()

        # Handle Mock Mode
        if self.force_mock or self.api_key == "mock":
            latency = (time.time() - start_time) * 1000
            return STTResult(
                success=True,
                transcript="Mujhe ek kilo chini aur do packet Maggi dena",
                detected_language="hi-IN",
                processing_time_ms=120.0,
                latency_ms=round(latency, 2),
                request_id="mock-prisma-req-001"
            )

        if not self.api_key:
            return STTResult(
                success=False,
                error_message="GNANI_API_KEY is not configured on the backend."
            )

        headers = {
            "X-API-Key-ID": self.api_key,
            "User-Agent": "DukaanSaathi/1.0"
        }

        files = {
            "audio_file": (filename, audio_bytes, "audio/wav")
        }

        data = {
            "model": "prisma-v3.0",
            "language_code": language_code,
            "format": format_mode
        }

        # Up to 3 attempts with exponential backoff on transient 403 / 5xx / timeout
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            start_time = time.time()
            try:
                resp = requests.post(
                    self.endpoint_url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=(3.0, float(self.timeout_seconds))
                )
                roundtrip_ms = (time.time() - start_time) * 1000

                if resp.status_code == 200:
                    result = resp.json()
                    transcript = result.get("transcript", "").strip()
                    detected_lang = result.get("detected_language_code", "hi-IN")
                    proc_time = result.get("processing_time", 0.0)
                    proc_time_ms = proc_time * 1000 if isinstance(proc_time, (int, float)) else 0.0
                    req_id = result.get("request_id")

                    return STTResult(
                        success=True,
                        transcript=transcript,
                        detected_language=detected_lang,
                        processing_time_ms=round(proc_time_ms, 2),
                        latency_ms=round(roundtrip_ms, 2),
                        request_id=req_id
                    )
                elif resp.status_code in [403, 429, 500, 502, 503, 504] and attempt < max_attempts:
                    logger.warning(
                        "Prisma STT transient %d (attempt %d/%d). Retrying in %.1fs...",
                        resp.status_code, attempt, max_attempts, 0.5 * attempt
                    )
                    time.sleep(0.5 * attempt)
                    continue
                else:
                    # Provide clean human-friendly message if Cloudflare HTML page was returned
                    raw_err = resp.text.strip()
                    if raw_err.startswith("<!DOCTYPE") or "<html" in raw_err:
                        err_msg = f"Prisma STT rate limited or gateway blocked (HTTP {resp.status_code})"
                    else:
                        err_msg = f"Prisma HTTP {resp.status_code}: {raw_err[:120]}"
                    logger.error(err_msg)
                    return STTResult(
                        success=False,
                        latency_ms=round(roundtrip_ms, 2),
                        error_message=err_msg
                    )

            except requests.Timeout:
                latency = (time.time() - start_time) * 1000
                if attempt < max_attempts:
                    logger.warning("Prisma STT timeout (attempt %d/%d). Retrying...", attempt, max_attempts)
                    time.sleep(0.5 * attempt)
                    continue
                err_msg = f"Prisma STT request timed out after {self.timeout_seconds}s"
                logger.error(err_msg)
                return STTResult(
                    success=False,
                    latency_ms=round(latency, 2),
                    error_message=err_msg
                )
            except Exception as e:
                latency = (time.time() - start_time) * 1000
                if attempt < max_attempts:
                    logger.warning("Prisma STT error %s (attempt %d/%d). Retrying...", e, attempt, max_attempts)
                    time.sleep(0.5 * attempt)
                    continue
                err_msg = f"Prisma STT connection failed: {e}"
                logger.error(err_msg)
                return STTResult(
                    success=False,
                    latency_ms=round(latency, 2),
                    error_message=err_msg
                )

        return STTResult(
            success=False,
            latency_ms=0.0,
            error_message="Prisma STT service temporarily unavailable. Please try speaking again."
        )
