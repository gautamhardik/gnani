"""
DukaanSaathi — Phase 8 Complete Voice Pipeline Performance & Latency Benchmark
Workstream 6: 30 Representative Complete Voice-Turn Trials

Measures:
1. upload_ms
2. preprocessing_ms (WAV vs WebM FFmpeg conversion)
3. prisma_rtt_ms (Live Gnani Prisma STT)
4. intelligence_ms (Deterministic Order Intelligence Engine)
5. timbre_ms (Live Gnani Timbre TTS)
6. total_server_ms
7. time_to_audible_ms (total_server_ms + audio retrieval)

Computes: sample count, min, max, median, p90, p95, failure count.
Investigates Phase 7 preprocessing overhead (1.17s mean) and compares
direct compliant WAV vs browser WebM Opus conversion.
"""

import io
import json
import logging
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import settings
from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models import StoreInventory
from backend.scripts.seed_db import seed_database
from backend.app.services.text_to_speech import TimbreTTSService

VOICE_CASES_PATH = ROOT / "data" / "data" / "voice_test_cases.json"
RESULTS_OUTPUT_PATH = ROOT / "data" / "benchmarks" / "phase_8_performance_trials.json"


def convert_wav_to_webm(wav_bytes: bytes) -> bytes:
    """Converts WAV bytes to browser WebM/Opus via FFmpeg."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as in_f:
        in_path = in_f.name
        in_f.write(wav_bytes)

    out_fd, out_path = tempfile.mkstemp(suffix=".webm")
    os.close(out_fd)

    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", in_path,
            "-c:a", "libopus",
            "-b:a", "32k",
            out_path
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=10)
        if res.returncode != 0:
            return wav_bytes
        with open(out_path, "rb") as f:
            return f.read()
    except Exception:
        return wav_bytes
    finally:
        for p in (in_path, out_path):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


def percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_d = sorted(data)
    idx = (len(sorted_d) - 1) * (p / 100.0)
    floor_idx = math.floor(idx)
    ceil_idx = math.ceil(idx)
    if floor_idx == ceil_idx:
        return sorted_d[int(idx)]
    d0 = sorted_d[floor_idx] * (ceil_idx - idx)
    d1 = sorted_d[ceil_idx] * (idx - floor_idx)
    return d0 + d1


def run_trials():
    api_key = settings.GNANI_API_KEY
    if not api_key or api_key == "mock":
        print("[FATAL] Phase 8 Performance Benchmark requires real GNANI_API_KEY in .env.")
        sys.exit(1)

    with open(VOICE_CASES_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    # Use all 30 cases
    print("=" * 80)
    print("DukaanSaathi — Phase 8 Complete Voice Pipeline Performance Trials")
    print(f"Target Utterances: {len(cases)} cases (TC001 - TC030)")
    print(f"Prisma Target:     {settings.GNANI_PRISMA_ENDPOINT}")
    print(f"Timbre Target:     {settings.GNANI_TIMBRE_ENDPOINT}")
    print("=" * 80)

    # In-memory test DB fixture
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    seed_database(db, bind_engine=test_engine)
    db.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    tts = TimbreTTSService(api_key=api_key, force_mock=False)
    trials: List[Dict[str, Any]] = []

    session_id = f"SESS_P8_PERF_{int(time.time())}"

    # Alternate formats between WAV and WebM to directly compare transcoding overhead
    for i, case in enumerate(cases, 1):
        case_id = case["case_id"]
        utterance = case["utterance"]
        # Half as webm, half as wav to directly measure conversion impact
        fmt = "webm" if i % 2 == 1 else "wav"

        print(f"[{i:02d}/30] Executing {case_id} ({fmt.upper()}): \"{utterance}\"")

        # 1. Synthesize reference spoken audio for testing the complete pipeline
        synth_t0 = time.time()
        synth_res = tts.synthesize(text=utterance, voice="Nalini", language="hi-IN")
        if not synth_res.success or not synth_res.audio_bytes:
            print(f"       [WARN] Synthesis failed for {case_id}: {synth_res.error_message}")
            continue

        raw_audio = synth_res.audio_bytes
        content_type = "audio/wav"
        filename = f"{case_id}.wav"

        if fmt == "webm":
            raw_audio = convert_wav_to_webm(raw_audio)
            content_type = "audio/webm"
            filename = f"{case_id}.webm"

        # 2. Execute voice turn call
        call_t0 = time.time()
        resp = client.post(
            f"/api/v1/voice/sessions/{session_id}/turn",
            files={"audio_file": (filename, raw_audio, content_type)},
            data={
                "client_turn_id": f"turn_p8_{i}",
                "include_audio_base64": "false",
                "force_mock": "false"
            }
        )
        roundtrip_total_ms = (time.time() - call_t0) * 1000

        if resp.status_code != 200:
            print(f"       [FAIL] HTTP {resp.status_code}: {resp.text}")
            trials.append({
                "case_id": case_id,
                "format": fmt,
                "success": False,
                "status_code": resp.status_code,
                "error": resp.text
            })
            continue

        turn_data = resp.json()
        audio_url = turn_data.get("audio_url")
        audio_retrieval_ms = 0.0

        if audio_url:
            t_aud0 = time.time()
            aud_resp = client.get(audio_url)
            audio_retrieval_ms = (time.time() - t_aud0) * 1000

        time_to_audible_ms = roundtrip_total_ms + audio_retrieval_ms
        lat = turn_data.get("latency_ms", {})

        trial_record = {
            "case_id": case_id,
            "format": fmt,
            "success": True,
            "spoken_input": utterance,
            "transcript": turn_data.get("transcript", ""),
            "intent": turn_data.get("intent", ""),
            "action": turn_data.get("action", ""),
            "audio_status": turn_data.get("audio_status", ""),
            "upload_ms": lat.get("upload_ms", 0.0),
            "preprocessing_ms": lat.get("preprocessing_ms", 0.0),
            "prisma_rtt_ms": lat.get("stt_ms", 0.0),
            "intelligence_ms": lat.get("intelligence_ms", 0.0),
            "timbre_ms": lat.get("tts_ms", 0.0),
            "total_server_ms": lat.get("total_ms", roundtrip_total_ms),
            "time_to_audible_ms": round(time_to_audible_ms, 2)
        }
        trials.append(trial_record)

        print(f"       -> Preproc: {trial_record['preprocessing_ms']:.1f}ms | Prisma: {trial_record['prisma_rtt_ms']:.1f}ms | Intel: {trial_record['intelligence_ms']:.1f}ms | Timbre: {trial_record['timbre_ms']:.1f}ms | Total: {trial_record['total_server_ms']:.1f}ms")

        # Brief rate-limiting pause to avoid hitting provider burst rate limits
        time.sleep(0.3)

    # 3. Compute Statistical Summaries
    successful = [t for t in trials if t.get("success")]
    sample_count = len(successful)
    fail_count = len(trials) - sample_count

    wav_successful = [t for t in successful if t["format"] == "wav"]
    webm_successful = [t for t in successful if t["format"] == "webm"]

    def stats_for(metric_key: str, dataset: List[Dict[str, Any]]):
        vals = [t[metric_key] for t in dataset]
        if not vals:
            return {"min": 0, "max": 0, "median": 0, "p90": 0, "p95": 0, "mean": 0}
        return {
            "min": round(min(vals), 2),
            "max": round(max(vals), 2),
            "mean": round(sum(vals) / len(vals), 2),
            "median": round(percentile(vals, 50), 2),
            "p90": round(percentile(vals, 90), 2),
            "p95": round(percentile(vals, 95), 2),
        }

    overall_stats = {
        "upload_ms": stats_for("upload_ms", successful),
        "preprocessing_ms": stats_for("preprocessing_ms", successful),
        "prisma_rtt_ms": stats_for("prisma_rtt_ms", successful),
        "intelligence_ms": stats_for("intelligence_ms", successful),
        "timbre_ms": stats_for("timbre_ms", successful),
        "total_server_ms": stats_for("total_server_ms", successful),
        "time_to_audible_ms": stats_for("time_to_audible_ms", successful),
    }

    wav_preproc = stats_for("preprocessing_ms", wav_successful)
    webm_preproc = stats_for("preprocessing_ms", webm_successful)

    report_payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_trials": len(trials),
        "successful_trials": sample_count,
        "failed_trials": fail_count,
        "targets": {
            "median_total_server_s": 4.0,
            "p95_total_server_s": 10.0,
            "intelligence_ms": 250.0
        },
        "overall_stats": overall_stats,
        "format_comparison": {
            "wav_preprocessing": wav_preproc,
            "webm_preprocessing": webm_preproc,
            "overhead_ratio": round(webm_preproc["mean"] / max(0.01, wav_preproc["mean"]), 1)
        },
        "trials": trials
    }

    RESULTS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("PHASE 8 PERFORMANCE STATISTICAL SUMMARY (30 Complete Voice Turns)")
    print("=" * 80)
    print(f"Total Trials: {len(trials)} | Successful: {sample_count} | Failures: {fail_count}")
    print(f"Preprocessing (WAV):  Mean={wav_preproc['mean']}ms, Median={wav_preproc['median']}ms, p95={wav_preproc['p95']}ms")
    print(f"Preprocessing (WebM): Mean={webm_preproc['mean']}ms, Median={webm_preproc['median']}ms, p95={webm_preproc['p95']}ms")
    print(f"Prisma STT RTT:       Mean={overall_stats['prisma_rtt_ms']['mean']}ms, Median={overall_stats['prisma_rtt_ms']['median']}ms, p95={overall_stats['prisma_rtt_ms']['p95']}ms")
    print(f"Order Intelligence:   Mean={overall_stats['intelligence_ms']['mean']}ms, Median={overall_stats['intelligence_ms']['median']}ms, p95={overall_stats['intelligence_ms']['p95']}ms")
    print(f"Timbre TTS Synthesis: Mean={overall_stats['timbre_ms']['mean']}ms, Median={overall_stats['timbre_ms']['median']}ms, p95={overall_stats['timbre_ms']['p95']}ms")
    print(f"Total Server Time:    Mean={overall_stats['total_server_ms']['mean']}ms, Median={overall_stats['total_server_ms']['median']}ms, p95={overall_stats['total_server_ms']['p95']}ms")
    print(f"Time to Audible:      Mean={overall_stats['time_to_audible_ms']['mean']}ms, Median={overall_stats['time_to_audible_ms']['median']}ms, p95={overall_stats['time_to_audible_ms']['p95']}ms")
    print("=" * 80)
    print(f"Results saved to: {RESULTS_OUTPUT_PATH}\n")


if __name__ == "__main__":
    run_trials()
