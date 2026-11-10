"""
Live smoke tests for Phase 4 Voice Pipeline using actual Gnani Prisma and Timbre APIs.
Explicitly labelled as LIVE. Uses real API credentials.
"""

import os
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.main import app
from tests.voice.test_audio_service import make_dummy_wav

LIVE_AVAILABLE = bool(settings.GNANI_API_KEY and settings.GNANI_API_KEY != "mock")


@pytest.mark.skipif(not LIVE_AVAILABLE, reason="GNANI_API_KEY required for live smoke tests")
def test_live_voice_turn_prisma_and_timbre(client: TestClient):
    """
    Smoke test: Sends live audio to Prisma STT and synthesizes response via Timbre TTS.
    """
    # 1.0s 16kHz mono audio
    wav_bytes = make_dummy_wav(duration_seconds=1.0)
    session_id = "SESS_LIVE_SMOKE_01"

    response = client.post(
        f"/api/v1/voice/sessions/{session_id}/turn",
        files={"audio_file": ("live_test.wav", wav_bytes, "audio/wav")},
        data={"force_mock": "false"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["session_id"] == session_id
    assert "latency_ms" in data
    assert data["latency_ms"]["stt_ms"] > 0
    assert data["audio_status"] in ["generated", "failed", "skipped_silence"]

    if data["audio_url"]:
        audio_resp = client.get(data["audio_url"])
        assert audio_resp.status_code == 200
        assert audio_resp.headers["Content-Type"] == "audio/wav"

