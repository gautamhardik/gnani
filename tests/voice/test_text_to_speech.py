"""
Unit tests for Gnani Timbre TTS Service (Phase 4 Task 7 & 9).
"""

from unittest.mock import MagicMock, patch
import pytest

from backend.app.services.text_to_speech import TimbreTTSService, TTSResult


def test_timbre_mock_mode():
    tts = TimbreTTSService(force_mock=True)
    res = tts.synthesize("Ji bhaiya, order confirm ho gaya hai.")

    assert res.success is True
    assert res.audio_bytes is not None
    assert res.audio_bytes.startswith(b"RIFF")
    assert res.audio_id is not None
    assert res.audio_id.startswith("aud_")

    # Verify audio is retrievable from cache
    cached = TimbreTTSService.get_cached_audio(res.audio_id)
    assert cached == res.audio_bytes


def test_timbre_empty_text():
    tts = TimbreTTSService(force_mock=True)
    res = tts.synthesize("   ")
    assert res.success is False
    assert "empty text" in res.error_message


def test_timbre_missing_api_key():
    tts = TimbreTTSService(api_key="", force_mock=False)
    res = tts.synthesize("Namaste")
    assert res.success is False
    assert "not configured" in res.error_message


@patch("backend.app.services.text_to_speech.requests.post")
def test_timbre_successful_binary_response(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"RIFF" + b"\x00" * 100
    mock_resp.headers = {"Content-Type": "audio/wav"}
    mock_post.return_value = mock_resp

    tts = TimbreTTSService(api_key="valid-test-key", force_mock=False)
    res = tts.synthesize("Ji bhaiya, samaan add kar diya hai.")

    assert res.success is True
    assert res.audio_bytes.startswith(b"RIFF")
    assert res.audio_id is not None


@patch("backend.app.services.text_to_speech.requests.post")
def test_timbre_http_error(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = '{"error": "Unsupported voice"}'
    mock_post.return_value = mock_resp

    tts = TimbreTTSService(api_key="valid-test-key", force_mock=False)
    res = tts.synthesize("Namaste")

    assert res.success is False
    assert "Timbre HTTP 400" in res.error_message
