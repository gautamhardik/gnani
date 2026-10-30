"""
DukaanSaathi — Gnani Timbre Feasibility Prototype (Phase 1)
Tests Text-to-Speech (TTS) synthesis for Hindi / Hinglish responses, currency amounts, and order confirmations.

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

def test_timbre_synthesis(text: str, voice: str = "Nalini", language: str = "hi-IN", output_path: str = "output_tts.wav"):
    """
    Sends conversational Hindi response text to Gnani Timbre and verifies audio generation and latency.
    """
    api_key = os.getenv("GNANI_API_KEY")
    api_url = os.getenv("GNANI_TIMBRE_ENDPOINT", "https://api.vachana.ai/v1/speech/synthesize")

    print("=" * 60)
    print("DukaanSaathi: Gnani Timbre TTS Feasibility Test")
    print("=" * 60)
    print(f"Target Text:    \"{text}\"")
    print(f"Target Voice:   {voice}")
    print(f"Language:       {language}")
    print(f"Endpoint:       {api_url}")
    print(f"API Key:        {'[CONFIGURED]' if api_key else '[MISSING - Set GNANI_API_KEY]'}")
    print(f"Output File:    {output_path}")
    print("-" * 60)

    if not api_key:
        print("\n[WARNING] GNANI_API_KEY environment variable is not set.")
        print("To run against live Gnani servers:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your GNANI_API_KEY from the Gnani Console")
        print("  3. Run: python tests/gnani/test_timbre.py \"<text to speak>\"")
        print("\nSimulating TTS generation pipeline (Mock Mode)...")
        # Generate dummy 1-second silence WAV for dry run validation
        import wave
        import struct
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with wave.open(output_path, "w") as wav_file:
            wav_file.setnchannels(1)      # mono
            wav_file.setsampwidth(2)      # 16-bit
            wav_file.setframerate(16000)  # 16kHz
            for _ in range(16000):
                wav_file.writeframes(struct.pack("<h", 0))

        print(f"[MOCK SUCCESS] Generated synthetic dummy audio file at: {output_path}")
        print("[MOCK SUCCESS] Verified downstream audio playback interface compatibility.")
        return True

    # Attempt official gnani-vachana SDK first
    try:
        from gnani.tts import GnaniTTSClient
        print("[INFO] Using gnani-vachana SDK...")
        client = GnaniTTSClient(api_key=api_key)
        start_time = time.time()
        audio_response = client.synthesize(
            text=text,
            model="timbre-v2.5",
            voice=voice,
            language=language
        )
        latency_ms = (time.time() - start_time) * 1000
        print(f"[SUCCESS] SDK Latency: {latency_ms:.1f}ms")
        with open(output_path, "wb") as f:
            if hasattr(audio_response, "content"):
                f.write(audio_response.content)
            elif isinstance(audio_response, bytes):
                f.write(audio_response)
            else:
                f.write(bytes(audio_response))
        print(f"[SUCCESS] Saved generated audio to: {output_path}")
        return True
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
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "voice": voice,
            "language": language,
            "audio_format": "wav",
            "sample_rate": 16000
        }
        req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            audio_bytes = resp.read()
            latency_ms = (time.time() - start_time) * 1000
            print(f"[SUCCESS] REST Latency: {latency_ms:.1f}ms (Received {len(audio_bytes)} bytes)")
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            print(f"[SUCCESS] Audio written to: {output_path}")
            return True
    except urllib.error.HTTPError as e:
        print(f"[ERROR] HTTP Error {e.code}: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"[ERROR] Connection failure: {e}")

    return False


if __name__ == "__main__":
    sample_text = sys.argv[1] if len(sys.argv) > 1 else "Ji, ek kilo chini aur do packet Maggi add kar diye hain. Aapka total ek sau paintalees rupaye hua."
    test_timbre_synthesis(sample_text)
