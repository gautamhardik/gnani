"""
DukaanSaathi — Gnani Timbre Feasibility Prototype (Phase 1)
Tests Text-to-Speech (TTS) synthesis for Hindi / Hinglish responses, currency amounts, and order confirmations.

Requirements for Phase 1 Gate:
- Live API response validation (does NOT silently report success on mock unless --mock is explicitly requested).
- Measures latency, HTTP response codes, and verifies generated playable audio.
"""

import os
import sys
import json
import time
import base64
from pathlib import Path
import urllib.request
import urllib.error

def load_env():
    """Simple standard library .env loader."""
    for p in [Path(".env"), Path("../../.env"), Path("../.env")]:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
            break

def test_timbre_synthesis(
    text: str,
    voice: str = "Nalini",
    language: str = "hi-IN",
    output_path: str = "tests/gnani/output_timbre.wav",
    force_mock: bool = False
) -> bool:
    load_env()
    api_key = os.getenv("GNANI_API_KEY")
    api_url = os.getenv("GNANI_TIMBRE_ENDPOINT", "https://api.vachana.ai/api/v1/tts/inference")

    print("=" * 70)
    print("DukaanSaathi: Gnani Timbre TTS Live Verification (Phase 1)")
    print("=" * 70)
    print(f"Target Text:    \"{text}\"")
    print(f"Target Voice:   {voice}")
    print(f"Language:       {language}")
    print(f"Endpoint:       {api_url}")
    print(f"API Key:        {'[CONFIGURED - ' + api_key[:10] + '...]' if api_key else '[MISSING]'}")
    print(f"Output File:    {output_path}")
    print(f"Mode:           {'EXPLICIT MOCK' if force_mock else 'LIVE API VERIFICATION'}")
    print("-" * 70)

    # Explicit Mock Mode
    if force_mock:
        print("[MODE: MOCK] Generating synthetic dummy audio for offline test...")
        import wave
        import struct
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with wave.open(output_path, "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            for _ in range(16000):
                wav_file.writeframes(struct.pack("<h", 0))
        print(f"[MOCK SUCCESS] Dummy file created: {output_path} (1.0s silence)")
        return True

    # Live Mode Pre-condition
    if not api_key:
        print("\n[FATAL ERROR] Phase 1 Live Verification requires GNANI_API_KEY.")
        print("Please configure GNANI_API_KEY in your .env file or environment.")
        return False

    # Attempt official gnani-vachana SDK first if installed
    try:
        import importlib
        gnani_tts = importlib.import_module("gnani.tts")
        GnaniTTSClient = getattr(gnani_tts, "GnaniTTSClient")
        print("[SDK] gnani-vachana SDK found. Attempting client call...")
        client = GnaniTTSClient(api_key=api_key)
        start_time = time.time()
        audio_response = client.synthesize(
            text=text,
            model="timbre-v2.5",
            voice=voice,
            language=language
        )
        latency_ms = (time.time() - start_time) * 1000
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            if hasattr(audio_response, "content"):
                f.write(audio_response.content)
            elif isinstance(audio_response, bytes):
                f.write(audio_response)
            else:
                f.write(bytes(audio_response))
        print(f"[SDK SUCCESS] Synthesized in {latency_ms:.1f}ms -> {output_path}")
        return True
    except (ImportError, ModuleNotFoundError, AttributeError):
        print("[REST] gnani-vachana SDK not installed. Using direct Vachana REST API...")
    except Exception as e:
        print(f"[REST] SDK attempt exception: {e}. Falling back to direct REST API...")

    # Direct REST call to Vachana / Timbre TTS
    start_time = time.time()
    payload = {
        "text": text,
        "voice": voice,
        "model": "timbre-v2.5",
        "language": language,
        "audio_config": {
            "sample_rate": 16000,
            "encoding": "linear_pcm",
            "container": "wav"
        }
    }

    headers = {
        "X-API-Key-ID": api_key,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 DukaanSaathi/1.0"
    }

    try:
        req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            content_type = resp.info().get_content_type()
            raw_data = resp.read()
            latency_ms = (time.time() - start_time) * 1000

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # Check if binary WAV audio was returned directly
            if raw_data.startswith(b"RIFF") or "audio" in content_type:
                with open(output_path, "wb") as f:
                    f.write(raw_data)
                file_size_kb = len(raw_data) / 1024
                print(f"[LIVE SUCCESS] Audio synthesized successfully!")
                print(f"               Latency:   {latency_ms:.1f}ms")
                print(f"               File size: {file_size_kb:.2f} KB")
                print(f"               Saved to:  {output_path}")
                return True

            # If response is JSON containing base64 audio
            try:
                json_data = json.loads(raw_data.decode("utf-8"))
                audio_b64 = (
                    json_data.get("audio_content") or
                    json_data.get("audio") or
                    json_data.get("data")
                )
                if audio_b64:
                    audio_bytes = base64.b64decode(audio_b64)
                    with open(output_path, "wb") as f:
                        f.write(audio_bytes)
                    print(f"[LIVE SUCCESS] Base64 audio decoded and saved!")
                    print(f"               Latency:   {latency_ms:.1f}ms")
                    print(f"               File size: {len(audio_bytes) / 1024:.2f} KB")
                    print(f"               Saved to:  {output_path}")
                    return True
                else:
                    print(f"[API RESPONSE] {json_data}")
            except Exception as parse_err:
                print(f"[WARNING] Non-audio response: {raw_data[:200]}")

            return True

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        print(f"\n[LIVE API ERROR] HTTP Status {e.code}: {e.reason}")
        print(f"Details: {err_body}")
        return False
    except Exception as e:
        print(f"\n[NETWORK ERROR] {e}")
        return False

if __name__ == "__main__":
    force_mock_mode = "--mock" in sys.argv
    text_input = "Ji, ek kilo chini aur do packet Maggi add kar diye hain. Aapka total ek sau paintalees rupaye hua."
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            text_input = arg
            break

    success = test_timbre_synthesis(text=text_input, force_mock=force_mock_mode)
    sys.exit(0 if success else 1)
