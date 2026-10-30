"""
Unit tests for Gnani Prisma STT Service (Phase 4 Task 3).
"""

from unittest.mock import MagicMock, patch
import pytest

from backend.app.services.speech_to_text import PrismaSTTService, STTResult


def test_prisma_mock_mode():
    stt = PrismaSTTService(force_mock=True)
    res = stt.transcribe(b"dummy_wav_data")
    assert res.success is True
    assert "chini" in res.transcript
    assert res.detected_language == "hi-IN"
    assert res.latency_ms >= 0


def test_prisma_missing_api_key():
    stt = PrismaSTTService(api_key="", force_mock=False)
    res = stt.transcribe(b"dummy_wav_data")
    assert res.success is False
    assert "not configured" in res.error_message


@patch("backend.app.services.speech_to_text.requests.post")
def test_prisma_successful_response(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "success": True,
        "request_id": "test-req-123",
        "transcript": "एक किलो चीनी देना",
        "detected_language_code": "hi-IN",
        "processing_time": 0.35
    }
    mock_post.return_value = mock_resp

    stt = PrismaSTTService(api_key="valid-test-key", force_mock=False)
    res = stt.transcribe(b"dummy_wav_data")

    assert res.success is True
    assert res.transcript == "एक किलो चीनी देना"
    assert res.detected_language == "hi-IN"
    assert res.processing_time_ms == pytest.approx(350.0, rel=1e-2)
    assert res.request_id == "test-req-123"


@patch("backend.app.services.speech_to_text.requests.post")
def test_prisma_http_error(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    mock_post.return_value = mock_resp

    stt = PrismaSTTService(api_key="valid-test-key", force_mock=False)
    res = stt.transcribe(b"dummy_wav_data")

    assert res.success is False
    assert "Prisma HTTP 500" in res.error_message
