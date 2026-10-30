"""
DukaanSaathi — Gnani Prisma Feasibility Prototype (Phase 1)
Tests Speech-to-Text (ASR) with Hindi / Hinglish grocery orders.

Supports:
1. Official `gnani-vachana` SDK if installed.
2. Direct REST API calls to Gnani API endpoints (`api.vachana.ai` / `api.gnani.ai`).
3. Synthetic / Mock mode for local unit testing without active API credits.
"""

import os
import sys
import json
import time
from pathlib import Path

def test_prisma_transcription(audio_file_path: str, model_version: str = "prisma-v3.0", language: str = "hi-IN"):
    """
    Sends an audio file to Gnani Prisma and benchmarks latency, transcript accuracy, and response structure.
    """
    api_key = os.getenv("GNANI_API_KEY")
    api_url = os.getenv("GNANI_PRISMA_ENDPOINT", "https://api.vachana.ai/v1/speech/transcribe")

    print("=" * 60)
    print("DukaanSaathi: Gnani Prisma STT Feasibility Test")
    print("=" * 60)
    print(f"Target Audio: {audio_file_path}")
    print(f"Target Model: {model_version}")
    print(f"Language:     {language}")
    print(f"Endpoint:     {api_url}")
    print(f"API Key:      {'[CONFIGURED]' if api_key else '[MISSING - Set GNANI_API_KEY]'}")
    print("-" * 60)

    if not api_key:
        print("\n[WARNING] GNANI_API_KEY environment variable is not set.")
        print("To run against live Gnani servers:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your GNANI_API_KEY from the Gnani Console")
        print("  3. Run: python tests/gnani/test_prisma.py <path_to_audio_file>")
        print("\nExecuting dry-run validation against mock payload structure...")
        
        # Simulated response matching Gnani Prisma output format
        mock_response = {
            "status": "success",
            "model": model_version,
            "language_detected": "hi-IN",
            "transcript": "Bhaiya ek kilo chini aur do packet Maggi dena",
            "confidence": 0.94,
            "turnaround_time_ms": 782,
            "words": [
                {"word": "Bhaiya", "start": 0.1, "end": 0.4},
                {"word": "ek", "start": 0.5, "end": 0.7},
                {"word": "kilo", "start": 0.8, "end": 1.1},
                {"word": "chini", "start": 1.2, "end": 1.6},
                {"word": "aur", "start": 1.7, "end": 1.9},
                {"word": "do", "start": 2.0, "end": 2.2},
                {"word": "packet", "start": 2.3, "end": 2.7},
                {"word": "Maggi", "start": 2.8, "end": 3.2},
                {"word": "dena", "start": 3.3, "end": 3.6}
            ]
        }
        print(f"\n[MOCK RESULT] Transcribed: \"{mock_response['transcript']}\"")
        print(f"[MOCK RESULT] Confidence:  {mock_response['confidence']}")
        return mock_response

    # Verify audio file exists
    audio_path = Path(audio_file_path)
    if not audio_path.exists():
        print(f"[ERROR] Audio file not found at: {audio_file_path}")
        return None

    # Attempt official gnani-vachana SDK first
    try:
        from gnani.stt import GnaniSTTClient
        print("[INFO] Using gnani-vachana SDK...")
        client = GnaniSTTClient(api_key=api_key)
        start_time = time.time()
        result = client.transcribe(str(audio_path), model=model_version, language_code=language)
        latency_ms = (time.time() - start_time) * 1000
        print(f"[SUCCESS] Latency: {latency_ms:.1f}ms")
        print(f"[TRANSCRIPT] {result.get('transcript', '')}")
        return result
    except ImportError:
        print("[INFO] gnani-vachana SDK not installed; falling back to direct HTTP REST request...")
    except Exception as e:
        print(f"[WARNING] SDK call error: {e}. Falling back to direct HTTP REST request...")

    # Direct REST call using requests / urllib
    import urllib.request
    import urllib.error

    start_time = time.time()
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "x-api-key": api_key
        }
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        req = urllib.request.Request(
            api_url,
            data=audio_bytes,
            headers={**headers, "Content-Type": "audio/wav"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode("utf-8")
            latency_ms = (time.time() - start_time) * 1000
            result = json.loads(data)
            print(f"[SUCCESS] REST Latency: {latency_ms:.1f}ms")
            print(f"[TRANSCRIPT] {result}")
            return result
    except urllib.error.HTTPError as e:
        print(f"[ERROR] HTTP Error {e.code}: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"[ERROR] Connection failure: {e}")

    return None


if __name__ == "__main__":
    audio_arg = sys.argv[1] if len(sys.argv) > 1 else "data/audio/sample_order.wav"
    test_prisma_transcription(audio_arg)
