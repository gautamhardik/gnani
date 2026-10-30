"""
Unit tests for Audio Ingestion & Preprocessing Service (Phase 4 Task 1 & 2).
"""

import io
import struct
import wave
import pytest

from backend.app.services.audio_service import (
    AudioService,
    AudioValidationError,
    MIN_AUDIO_BYTES,
    MAX_AUDIO_BYTES,
)


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


def test_detect_format_wav():
    wav_bytes = make_dummy_wav(0.5)
    fmt = AudioService.detect_format(wav_bytes)
    assert fmt == "wav"


def test_detect_format_magic_bytes():
    # WebM header
    webm_bytes = b"\x1a\x45\xdf\xa3" + b"\x00" * 100
    assert AudioService.detect_format(webm_bytes) == "webm"

    # OGG header
    ogg_bytes = b"OggS" + b"\x00" * 100
    assert AudioService.detect_format(ogg_bytes) == "ogg"

    # MP3 header
    mp3_bytes = b"ID3" + b"\x00" * 100
    assert AudioService.detect_format(mp3_bytes) == "mp3"


def test_validate_audio_upload_rejections():
    # Too small
    with pytest.raises(AudioValidationError, match="too small"):
        AudioService.validate_audio_upload(b"tiny")

    # Non-audio formats
    with pytest.raises(AudioValidationError, match="not a supported audio format"):
        AudioService.validate_audio_upload(b"%PDF-1.4 file contents here..." + b"\x00" * 50)

    with pytest.raises(AudioValidationError, match="not a supported audio format"):
        AudioService.validate_audio_upload(b"<html><body>Not an audio file</body></html>" + b" " * 50)


def test_inspect_audio_wav():
    wav_bytes = make_dummy_wav(duration_seconds=1.5, sample_rate=16000, channels=1)
    meta = AudioService.inspect_audio(wav_bytes, format_hint="wav")
    assert meta.format == "wav"
    assert meta.duration_seconds == pytest.approx(1.5, rel=1e-2)
    assert meta.sample_rate == 16000
    assert meta.channels == 1
    assert meta.bit_depth == 16


def test_validate_duration_boundaries():
    # Below minimum (0.1s < 0.2s)
    short_meta = AudioService.inspect_audio(make_dummy_wav(0.1), format_hint="wav")
    with pytest.raises(AudioValidationError, match="too short"):
        AudioService.validate_duration(short_meta)

    # Valid duration (2.0s)
    valid_meta = AudioService.inspect_audio(make_dummy_wav(2.0), format_hint="wav")
    AudioService.validate_duration(valid_meta)  # Should not raise


def test_convert_to_pcm16_wav_bypass():
    """Conforming 16kHz mono WAV should bypass FFmpeg conversion directly."""
    wav_bytes = make_dummy_wav(duration_seconds=1.0, sample_rate=16000, channels=1)
    result_bytes = AudioService.convert_to_pcm16_wav(wav_bytes, original_format="wav")
    assert result_bytes == wav_bytes


def test_convert_stereo_44k_to_pcm16_mono():
    """Non-16k stereo WAV should be converted to 16kHz mono 16-bit PCM WAV."""
    stereo_bytes = make_dummy_wav(duration_seconds=0.5, sample_rate=44100, channels=2)
    converted = AudioService.convert_to_pcm16_wav(stereo_bytes, original_format="wav")

    assert converted.startswith(b"RIFF")
    with wave.open(io.BytesIO(converted), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 16000
        assert wf.getsampwidth() == 2
