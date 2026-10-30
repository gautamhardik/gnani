"""
DukaanSaathi — Gnani Prisma Feasibility Prototype (Phase 1)
Tests Speech-to-Text (ASR) with Hindi / Hinglish grocery orders.

Requirements for Phase 1 Gate:
- Live API response validation (does NOT silently report success on mock unless --mock is explicitly requested).
- Sends audio to Gnani Prisma (vachana.ai STT v3) with indic-auto / hi-IN and codemix formatting.
- Measures latency, HTTP response codes, and verifies returned transcript.
"""

import os
import sys
import json
import time
from pathlib import Path
import urllib.request
import urllib.error

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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

def test_prisma_transcription(
    audio_file_path: str,
    model_version: str = "prisma-v3.0",
    language: str = "indic-auto",
    format_mode: str = "codemix",
    output_json_path: str = "tests/gnani/prisma_live_result.json",
    force_mock: bool = False
) -> dict:
    load_env()
    api_key = os.getenv("GNANI_API_KEY")
    api_url = os.getenv("GNANI_PRISMA_ENDPOINT", "https://api.vachana.ai/stt/v3")

    print("=" * 70)
    print("DukaanSaathi: Gnani Prisma STT Live Verification (Phase 1)")
    print("=" * 70)
    print(f"Target Audio: {audio_file_path}")
    print(f"Target Model: {model_version}")
    print(f"Language:     {language}")
    print(f"Format Mode:  {format_mode}")
    print(f"Endpoint:     {api_url}")
    print(f"API Key:      {'[CONFIGURED - ' + api_key[:10] + '...]' if api_key else '[MISSING]'}")
    print(f"Mode:         {'EXPLICIT MOCK' if force_mock else 'LIVE API VERIFICATION'}")
    print("-" * 70)

    # Explicit Mock Mode
    if force_mock:
        print("[MODE: MOCK] Returning synthetic transcript payload for offline test...")
        mock_response = {
            "success": True,
            "mock": True,
            "request_id": "mock-req-001",
            "transcript": "Bhaiya ek kilo chini aur do packet Maggi dena",
            "model": model_version,
            "processing_time": 0.45,
            "end_to_end_latency": 0.48,
            "detected_language_code": "hi-IN"
        }
        print(f"[MOCK SUCCESS] Transcribed: \"{mock_response['transcript']}\"")
        return mock_response

    # Live Mode Pre-conditions
    if not api_key:
        print("\n[FATAL ERROR] Phase 1 Live Verification requires GNANI_API_KEY.")
        print("Please configure GNANI_API_KEY in your .env file or environment.")
        return None

    audio_path = Path(audio_file_path)
    if not audio_path.exists():
        print(f"[ERROR] Audio file not found at: {audio_file_path}")
        return None

    # Attempt official gnani-vachana SDK first if installed
    try:
        import importlib
        gnani_stt = importlib.import_module("gnani.stt")
        GnaniSTTClient = getattr(gnani_stt, "GnaniSTTClient")
        print("[SDK] gnani-vachana SDK found. Attempting client call...")
        client = GnaniSTTClient(api_key=api_key)
        start_time = time.time()
        result = client.transcribe(str(audio_path), model=model_version, language_code=language)
        latency_ms = (time.time() - start_time) * 1000
        print(f"[SDK SUCCESS] Latency: {latency_ms:.1f}ms")
        print(f"[SDK TRANSCRIPT] {result.get('transcript', '')}")
        return result
    except (ImportError, ModuleNotFoundError, AttributeError):
        print("[REST] gnani-vachana SDK not installed. Using direct Vachana REST API...")
    except Exception as e:
        print(f"[REST] SDK attempt exception: {e}. Falling back to direct REST API...")

    # Direct REST Call using multipart/form-data via requests / urllib
    start_time = time.time()
    try:
        import requests
        headers = {
            "X-API-Key-ID": api_key,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 DukaanSaathi/1.0"
        }
        with open(audio_path, "rb") as f:
            files = {
                "audio_file": (audio_path.name, f, "audio/wav")
            }
            data = {
                "model": model_version,
                "language_code": language,
                "format": format_mode
            }
            resp = requests.post(api_url, headers=headers, files=files, data=data, timeout=30)

        latency_ms = (time.time() - start_time) * 1000

        if resp.status_code == 200:
            result = resp.json()
            transcript = result.get("transcript", "")
            detected_lang = result.get("detected_language_code", "unknown")
            api_proc_time = result.get("processing_time", 0)

            print("[LIVE SUCCESS] Audio transcribed successfully!")
            print(f"               Transcript:       \"{transcript}\"")
            print(f"               Detected Lang:    {detected_lang}")
            print(f"               Server Proc Time: {api_proc_time * 1000:.1f}ms" if isinstance(api_proc_time, (int, float)) else f"               Server Proc Time: {api_proc_time}")
            print(f"               Round-trip Time:  {latency_ms:.1f}ms")

            # Persist result for verification audit
            Path(output_json_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_json_path, "w", encoding="utf-8") as jf:
                json.dump(result, jf, indent=2, ensure_ascii=False)
            print(f"               Saved report:     {output_json_path}")

            return result
        else:
            print(f"\n[LIVE API ERROR] HTTP {resp.status_code}: {resp.text}")
            return None

    except Exception as e:
        print(f"\n[CONNECTION ERROR] {e}")
        return None

if __name__ == "__main__":
    force_mock_mode = "--mock" in sys.argv
    audio_arg = "tests/gnani/output_timbre.wav"
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            audio_arg = arg
            break

    res = test_prisma_transcription(audio_arg, force_mock=force_mock_mode)
    sys.exit(0 if res and res.get("success") else 1)
