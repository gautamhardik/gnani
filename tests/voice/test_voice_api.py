"""
End-to-End API Integration Tests for Voice Turn Endpoint (Phase 4).
Tests audio upload, validation, mock/stubbed external providers, session persistence,
multi-turn conversation flow, duplicate handling, and error fallbacks.
"""

import io
import struct
import wave
from decimal import Decimal
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models import OrderSession, StoreInventory
from backend.app.services.audio_service import AudioService


def make_dummy_wav(duration_seconds: float = 1.0, sample_rate: int = 16000, channels: int = 1) -> bytes:
    """Helper to generate in-memory PCM 16-bit WAV audio."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        num_frames = int(duration_seconds * sample_rate)
        wf.writeframes(struct.pack("<h", 0) * num_frames * channels)
    return buf.getvalue()


def test_voice_turn_upload_and_audio_retrieval(client: TestClient, db_session):
    """Verifies complete voice turn cycle with audio synthesis and playback."""
    wav_bytes = make_dummy_wav(duration_seconds=1.0, sample_rate=16000, channels=1)

    with patch("backend.app.api.v1.voice.PrismaSTTService.transcribe") as mock_stt, \
         patch("backend.app.api.v1.voice.TimbreTTSService.synthesize") as mock_tts:

        mock_stt.return_value = MagicMock(
            success=True,
            transcript="Bhaiya ek kilo chini aur do packet Maggi dena",
            detected_language="hi-IN",
            processing_time_ms=250.0,
            latency_ms=300.0,
            request_id="test-req-001"
        )

        dummy_audio = make_dummy_wav(0.5)
        mock_tts.return_value = MagicMock(
            success=True,
            audio_bytes=dummy_audio,
            audio_format="audio/wav",
            latency_ms=450.0,
            audio_id="aud_mock_test_123",
            error_message=None
        )

        # Store dummy audio in cache
        from backend.app.services.text_to_speech import TimbreTTSService
        TimbreTTSService._audio_cache["aud_mock_test_123"] = (dummy_audio, 1000.0)

        response = client.post(
            "/api/v1/voice/sessions/SESS_VOICE_TEST_01/turn",
            files={"audio_file": ("test.wav", wav_bytes, "audio/wav")},
            data={"include_audio_base64": "true"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["session_id"] == "SESS_VOICE_TEST_01"
        assert data["transcript"] == "Bhaiya ek kilo chini aur do packet Maggi dena"
        assert data["detected_language"] == "hi-IN"
        assert data["intent"] == "add_items"
        assert data["action"] == "add_items"
        assert data["cart"]["item_count"] == 2
        assert Decimal(str(data["cart"]["total_amount"])) == Decimal("74.00")
        assert "chini" in data["assistant_text"].lower() or "add" in data["assistant_text"].lower()
        assert data["audio_status"] == "generated"
        assert data["audio_url"] == "/api/v1/voice/audio/aud_mock_test_123"
        assert data["audio_base64"] is not None

        # Verify latency breakdown
        lat = data["latency_ms"]
        assert lat["upload_ms"] >= 0
        assert lat["preprocessing_ms"] >= 0
        assert lat["stt_ms"] == 300.0
        assert lat["intelligence_ms"] >= 0
        assert lat["tts_ms"] == 450.0
        assert lat["total_ms"] > 0

        # Verify audio streaming endpoint
        audio_resp = client.get(data["audio_url"])
        assert audio_resp.status_code == 200
        assert audio_resp.headers["Content-Type"] == "audio/wav"
        assert audio_resp.content.startswith(b"RIFF")


def test_multi_turn_voice_flow_and_two_phase_invariant(client: TestClient, db_session):
    """
    Validates:
    1. Multi-turn additions and corrections persist across turns for the same session.
    2. Explicit confirmation changes session status to confirmed.
    3. TWO-PHASE COMMIT INVARIANT: Stock is NOT decremented during voice turns!
    """
    session_id = "SESS_VOICE_MULTITURN_01"
    wav_bytes = make_dummy_wav(duration_seconds=1.0)

    # Check starting stock for PRD034 (Loose Sugar)
    inv_sugar_before = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD034").first()
    initial_stock = float(inv_sugar_before.stock_quantity)

    # --- Turn 1: Ek kilo chini add karo ---
    with patch("backend.app.api.v1.voice.PrismaSTTService.transcribe") as mock_stt, \
         patch("backend.app.api.v1.voice.TimbreTTSService.synthesize") as mock_tts:

        mock_stt.return_value = MagicMock(
            success=True,
            transcript="Ek kilo chini add karo",
            detected_language="hi-IN",
            processing_time_ms=100.0,
            latency_ms=150.0
        )
        mock_tts.return_value = MagicMock(
            success=True, audio_bytes=wav_bytes, audio_format="audio/wav",
            latency_ms=200.0, audio_id="aud_t1", error_message=None
        )

        r1 = client.post(
            f"/api/v1/voice/sessions/{session_id}/turn",
            files={"audio_file": ("turn1.wav", wav_bytes, "audio/wav")}
        )
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["cart"]["item_count"] == 1
        assert float(d1["cart"]["items"][0]["quantity"]) == 1.0

    # --- Turn 2: Nahi, aadha kilo kar do (Correction) ---
    with patch("backend.app.api.v1.voice.PrismaSTTService.transcribe") as mock_stt, \
         patch("backend.app.api.v1.voice.TimbreTTSService.synthesize") as mock_tts:

        mock_stt.return_value = MagicMock(
            success=True,
            transcript="Nahi, aadha kilo kar do",
            detected_language="hi-IN",
            processing_time_ms=100.0,
            latency_ms=150.0
        )
        mock_tts.return_value = MagicMock(
            success=True, audio_bytes=wav_bytes, audio_format="audio/wav",
            latency_ms=200.0, audio_id="aud_t2", error_message=None
        )

        r2 = client.post(
            f"/api/v1/voice/sessions/{session_id}/turn",
            files={"audio_file": ("turn2.wav", wav_bytes, "audio/wav")}
        )
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["cart"]["item_count"] == 1
        assert float(d2["cart"]["items"][0]["quantity"]) == 0.5
        assert Decimal(str(d2["cart"]["total_amount"])) == Decimal("23.00")

    # --- Turn 3: Haan, order confirm kar do ---
    with patch("backend.app.api.v1.voice.PrismaSTTService.transcribe") as mock_stt, \
         patch("backend.app.api.v1.voice.TimbreTTSService.synthesize") as mock_tts:

        mock_stt.return_value = MagicMock(
            success=True,
            transcript="Haan, order confirm kar do",
            detected_language="hi-IN",
            processing_time_ms=100.0,
            latency_ms=150.0
        )
        mock_tts.return_value = MagicMock(
            success=True, audio_bytes=wav_bytes, audio_format="audio/wav",
            latency_ms=200.0, audio_id="aud_t3", error_message=None
        )

        r3 = client.post(
            f"/api/v1/voice/sessions/{session_id}/turn",
            files={"audio_file": ("turn3.wav", wav_bytes, "audio/wav")}
        )
        assert r3.status_code == 200
        d3 = r3.json()
        assert d3["session_state"] == "ORDER_PLACED"

    # Verify OrderSession in DB
    db_session.expire_all()
    sess = db_session.query(OrderSession).filter(OrderSession.session_id == session_id).first()
    assert sess.status == "confirmed"
    assert len(sess.current_cart) == 1
    assert sess.current_cart[0]["quantity"] == 0.5

    # VERIFY TWO-PHASE INVARIANT: Stock must NOT have changed!
    inv_sugar_after = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD034").first()
    assert float(inv_sugar_after.stock_quantity) == initial_stock


def test_idempotent_duplicate_request_retry(client: TestClient):
    """Ensures that sending the same client_turn_id returns cached response with is_duplicate=True."""
    wav_bytes = make_dummy_wav(duration_seconds=1.0)
    session_id = "SESS_IDEMPOTENT_01"
    turn_id = "turn_client_req_999"

    with patch("backend.app.api.v1.voice.PrismaSTTService.transcribe") as mock_stt, \
         patch("backend.app.api.v1.voice.TimbreTTSService.synthesize") as mock_tts:

        mock_stt.return_value = MagicMock(
            success=True, transcript="Ek kilo chini dena",
            detected_language="hi-IN", processing_time_ms=100.0, latency_ms=150.0
        )
        mock_tts.return_value = MagicMock(
            success=True, audio_bytes=wav_bytes, audio_format="audio/wav",
            latency_ms=200.0, audio_id="aud_idem_1", error_message=None
        )

        # First request
        r1 = client.post(
            f"/api/v1/voice/sessions/{session_id}/turn",
            files={"audio_file": ("turn.wav", wav_bytes, "audio/wav")},
            data={"client_turn_id": turn_id}
        )
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["is_duplicate"] is False

        # Duplicate retry with same client_turn_id
        r2 = client.post(
            f"/api/v1/voice/sessions/{session_id}/turn",
            files={"audio_file": ("turn.wav", wav_bytes, "audio/wav")},
            data={"client_turn_id": turn_id}
        )
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["is_duplicate"] is True
        assert d2["turn_id"] == turn_id
        assert d2["transcript"] == d1["transcript"]


def test_audio_upload_validation_errors(client: TestClient):
    """Uploads with corrupt, empty, or non-audio payloads must be rejected with 400."""
    session_id = "SESS_VAL_ERR"

    # Too small
    r_small = client.post(
        f"/api/v1/voice/sessions/{session_id}/turn",
        files={"audio_file": ("tiny.wav", b"too small", "audio/wav")}
    )
    assert r_small.status_code == 400
    assert "too small" in r_small.json()["detail"]

    # Non-audio PDF
    pdf_payload = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF" + b"\x00" * 100
    r_pdf = client.post(
        f"/api/v1/voice/sessions/{session_id}/turn",
        files={"audio_file": ("doc.pdf", pdf_payload, "application/pdf")}
    )
    assert r_pdf.status_code == 400
    assert "not a supported audio format" in r_pdf.json()["detail"]


def test_tts_failure_preserves_cart_and_returns_error_status(client: TestClient):
    """Task 9: If Timbre TTS fails, preserve processed order/cart and return audio_status='failed'."""
    wav_bytes = make_dummy_wav(duration_seconds=1.0)
    session_id = "SESS_TTS_FAIL"

    with patch("backend.app.api.v1.voice.PrismaSTTService.transcribe") as mock_stt, \
         patch("backend.app.api.v1.voice.TimbreTTSService.synthesize") as mock_tts:

        mock_stt.return_value = MagicMock(
            success=True, transcript="Ek kilo chini add karo",
            detected_language="hi-IN", processing_time_ms=100.0, latency_ms=150.0
        )
        # TTS fails
        mock_tts.return_value = MagicMock(
            success=False, audio_bytes=None, audio_id=None,
            latency_ms=210.0, error_message="Gnani Timbre service unreachable"
        )

        resp = client.post(
            f"/api/v1/voice/sessions/{session_id}/turn",
            files={"audio_file": ("turn.wav", wav_bytes, "audio/wav")}
        )

        assert resp.status_code == 200
        data = resp.json()

        # Cart must be successfully updated despite TTS failure!
        assert data["cart"]["item_count"] == 1
        assert data["cart"]["items"][0]["product_id"] == "PRD034"
        assert data["assistant_text"] != ""
        assert data["audio_status"] == "failed"
        assert data["audio_url"] is None
        assert "Audio generation unavailable" in data["warning"]
