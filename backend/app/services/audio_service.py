"""
DukaanSaathi — Audio Ingestion & Preprocessing Service (Phase 4 Task 1 & 2)
Validates MIME types, magic bytes, durations, and provides controlled FFmpeg
transcoding to 16kHz mono 16-bit linear PCM WAV for Gnani Prisma STT.
"""

import io
import json
import logging
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Optional, Tuple

from backend.app.schemas.voice import AudioMetadata

logger = logging.getLogger(__name__)

# Constants for audio validation
MIN_AUDIO_BYTES = 64
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
MIN_DURATION_SECONDS = 0.2
MAX_DURATION_SECONDS = 60.0


class AudioValidationError(ValueError):
    """Raised when an audio upload violates size, format, or duration constraints."""
    pass


class AudioService:
    @staticmethod
    def detect_format(file_bytes: bytes, filename: Optional[str] = None) -> str:
        """
        Detects audio container format using binary magic bytes and file extension fallback.
        """
        if len(file_bytes) < 4:
            raise AudioValidationError("Audio payload is too small to determine format.")

        header = file_bytes[:16]

        # WAV: starts with 'RIFF' and bytes 8..12 contain 'WAVE'
        if header.startswith(b"RIFF") and len(file_bytes) >= 12 and file_bytes[8:12] == b"WAVE":
            return "wav"

        # WebM / Matroska: starts with \x1a\x45\xdf\xa3
        if header.startswith(b"\x1a\x45\xdf\xa3"):
            return "webm"

        # Ogg: starts with 'OggS'
        if header.startswith(b"OggS"):
            return "ogg"

        # MP4 / M4A: bytes 4..8 usually contain 'ftyp'
        if len(file_bytes) >= 8 and file_bytes[4:8] == b"ftyp":
            return "mp4"

        # MP3: starts with 'ID3' or sync frame \xff\xfb, \xff\xf3, \xff\xf2
        if header.startswith(b"ID3") or (len(file_bytes) >= 2 and file_bytes[0] == 0xFF and (file_bytes[1] & 0xE0) == 0xE0):
            return "mp3"

        # Fallback to extension if valid
        if filename:
            ext = Path(filename).suffix.lower().lstrip(".")
            if ext in ["wav", "wave"]:
                return "wav"
            elif ext in ["webm"]:
                return "webm"
            elif ext in ["ogg", "opus"]:
                return "ogg"
            elif ext in ["mp4", "m4a", "aac"]:
                return "mp4"
            elif ext in ["mp3"]:
                return "mp3"

        # Explicitly check for non-audio common formats
        if header.startswith(b"PK\x03\x04") or header.startswith(b"%PDF") or header.startswith(b"<html") or header.startswith(b"<!DOC"):
            raise AudioValidationError("Uploaded file is not a supported audio format.")

        raise AudioValidationError("Unrecognized audio format. Supported: WAV, WebM, OGG, MP3, MP4/M4A.")

    @staticmethod
    def validate_audio_upload(
        file_bytes: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> str:
        """
        Performs initial size and format sanity checks on the raw incoming upload.
        Returns the detected container format string.
        """
        size = len(file_bytes)
        if size < MIN_AUDIO_BYTES:
            raise AudioValidationError(f"Audio file is too small ({size} bytes). Minimum required is {MIN_AUDIO_BYTES} bytes.")

        if size > MAX_AUDIO_BYTES:
            raise AudioValidationError(f"Audio file exceeds maximum allowed size of {MAX_AUDIO_BYTES // (1024*1024)}MB ({size} bytes).")

        fmt = AudioService.detect_format(file_bytes, filename=filename)
        return fmt

    @staticmethod
    def inspect_audio(file_bytes: bytes, format_hint: str = "wav") -> AudioMetadata:
        """
        Inspects duration, sample rate, channels, and size.
        Uses Python wave for standard WAV or ffprobe for complex/compressed containers.
        """
        # Fast path for standard WAV using wave module
        if format_hint == "wav":
            try:
                with wave.open(io.BytesIO(file_bytes), "rb") as wf:
                    channels = wf.getnchannels()
                    sample_rate = wf.getframerate()
                    sampwidth = wf.getsampwidth()
                    frames = wf.getnframes()
                    duration = frames / float(sample_rate) if sample_rate > 0 else 0.0
                    bit_depth = sampwidth * 8

                    # Guard against streaming chunk header artifacts (e.g. 0x7FFFFFFF or 0xFFFFFFFF)
                    if duration > 3600.0 or duration <= 0.0:
                        bytes_per_sec = sample_rate * channels * sampwidth
                        if bytes_per_sec > 0:
                            duration = max(0.0, (len(file_bytes) - 44)) / float(bytes_per_sec)

                    return AudioMetadata(
                        format="wav",
                        duration_seconds=round(duration, 3),
                        sample_rate=sample_rate,
                        channels=channels,
                        bit_depth=bit_depth,
                        file_size_bytes=len(file_bytes)
                    )
            except Exception:
                # Fallback to ffprobe if wave module cannot parse (e.g. non-standard WAV chunk)
                pass

        # Robust path: ffprobe
        ffprobe_bin = shutil.which("ffprobe") or "ffprobe"
        with tempfile.NamedTemporaryFile(suffix=f".{format_hint}", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(file_bytes)

        try:
            cmd = [
                ffprobe_bin,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                tmp_path
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode != 0:
                raise AudioValidationError("Failed to inspect audio metadata with ffprobe.")

            info = json.loads(res.stdout)
            fmt_info = info.get("format", {})
            streams = info.get("streams", [])
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

            duration = float(fmt_info.get("duration", audio_stream.get("duration", 0.0)))
            sample_rate = int(audio_stream.get("sample_rate", 16000))
            channels = int(audio_stream.get("channels", 1))

            return AudioMetadata(
                format=format_hint,
                duration_seconds=round(duration, 3),
                sample_rate=sample_rate,
                channels=channels,
                bit_depth=None,
                file_size_bytes=len(file_bytes)
            )
        except subprocess.TimeoutExpired:
            raise AudioValidationError("Audio metadata inspection timed out.")
        except Exception as e:
            raise AudioValidationError(f"Could not inspect audio file: {e}")
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    @staticmethod
    def validate_duration(metadata: AudioMetadata) -> None:
        """
        Validates duration against upper and lower bounds.
        """
        if metadata.duration_seconds < MIN_DURATION_SECONDS:
            raise AudioValidationError(
                f"Audio clip is too short ({metadata.duration_seconds:.2f}s). Minimum allowed is {MIN_DURATION_SECONDS}s."
            )
        if metadata.duration_seconds > MAX_DURATION_SECONDS:
            raise AudioValidationError(
                f"Audio clip exceeds maximum duration ({metadata.duration_seconds:.2f}s > {MAX_DURATION_SECONDS}s)."
            )

    @staticmethod
    def convert_to_pcm16_wav(file_bytes: bytes, original_format: str) -> bytes:
        """
        Ensures the audio is 16kHz mono 16-bit linear PCM WAV for Gnani Prisma STT.
        If already conforming, bypasses transcoding to preserve exact acoustic fidelity.
        Otherwise, performs controlled transcoding via FFmpeg.
        """
        # Fast path check for already compliant WAV
        if original_format == "wav":
            try:
                with wave.open(io.BytesIO(file_bytes), "rb") as wf:
                    if (
                        wf.getnchannels() == 1
                        and wf.getframerate() == 16000
                        and wf.getsampwidth() == 2
                    ):
                        logger.debug("Audio is already 16kHz mono PCM WAV. Bypassing FFmpeg.")
                        return file_bytes
            except Exception:
                pass

        # FFmpeg transcode path
        ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
        with tempfile.NamedTemporaryFile(suffix=f".{original_format}", delete=False) as in_tmp:
            in_path = in_tmp.name
            in_tmp.write(file_bytes)

        out_fd, out_path = tempfile.mkstemp(suffix=".wav")
        os.close(out_fd)

        try:
            cmd = [
                ffmpeg_bin,
                "-y",
                "-i", in_path,
                "-vn",
                "-ac", "1",
                "-ar", "16000",
                "-c:a", "pcm_s16le",
                out_path
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if proc.returncode != 0:
                logger.error(f"FFmpeg conversion failed: {proc.stderr}")
                raise AudioValidationError(f"Audio conversion failed: {proc.stderr.strip()[:200]}")

            with open(out_path, "rb") as f:
                converted_bytes = f.read()

            if not converted_bytes.startswith(b"RIFF"):
                raise AudioValidationError("Converted audio does not contain a valid WAV header.")

            return converted_bytes
        except subprocess.TimeoutExpired:
            raise AudioValidationError("Audio conversion timed out.")
        finally:
            for p in (in_path, out_path):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
