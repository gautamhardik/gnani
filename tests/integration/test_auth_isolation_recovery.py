"""
DukaanSaathi — Phase 7 Authentication, Isolation, Failure & Recovery Verification
TASKS 7 & 8:
- Security: 401 Unauthorized enforcement, customer isolation, zero frontend secret leaks.
- Resilience: Voice TTS failure recovery, input validation, and database error boundary.
"""

import os
from pathlib import Path
from unittest.mock import patch
import pytest

ROOT = Path(__file__).resolve().parents[2]

def test_unauthenticated_requests_to_merchant_endpoints_return_401(pg_client):
    """
    TASK 7: Unauthenticated requests to all protected merchant endpoints
    must be rejected with HTTP 401 Unauthorized.
    """
    protected_endpoints = [
        ("GET", "/api/v1/merchant/overview"),
        ("GET", "/api/v1/orders"),
        ("POST", "/api/v1/orders/ORD_DUMMY/accept"),
        ("POST", "/api/v1/orders/ORD_DUMMY/reject"),
        ("POST", "/api/v1/orders/ORD_DUMMY/status"),
        ("PUT", "/api/v1/inventory/PRD001"),
        ("GET", "/api/v1/inventory/movements"),
        ("POST", "/api/v1/products"),
        ("PUT", "/api/v1/products/PRD001"),
        ("DELETE", "/api/v1/products/PRD001"),
    ]

    for method, endpoint in protected_endpoints:
        if method == "GET":
            resp = pg_client.get(endpoint)
        elif method == "POST":
            resp = pg_client.post(endpoint, json={})
        elif method == "PUT":
            resp = pg_client.put(endpoint, json={})
        elif method == "DELETE":
            resp = pg_client.delete(endpoint)

        assert resp.status_code == 401, (
            f"Endpoint {method} {endpoint} did not return 401 when called without credentials! Got: {resp.status_code}"
        )


def test_invalid_bearer_token_rejected_with_401(pg_client):
    """
    TASK 7: Tampered or invalid bearer tokens must be rejected.
    """
    bad_headers = {"Authorization": "Bearer forged-or-expired-jwt-token"}
    resp = pg_client.get("/api/v1/merchant/overview", headers=bad_headers)
    assert resp.status_code == 401


def test_customer_cannot_call_merchant_actions(pg_client):
    """
    TASK 7: Public customer ordering flow cannot execute merchant mutations.
    """
    # Customer can create session and place order without auth
    order_resp = pg_client.post("/api/v1/orders", json={
        "store_id": "STORE001",
        "items": [{"product_id": "PRD001", "quantity": 1.0}]
    })
    assert order_resp.status_code in (200, 201)
    order_id = order_resp.json()["order_id"]

    # But customer cannot self-accept the order without merchant token
    self_accept_resp = pg_client.post(f"/api/v1/orders/{order_id}/accept")
    assert self_accept_resp.status_code == 401


def test_frontend_bundle_and_env_contain_no_server_secrets():
    """
    TASK 7: Scan frontend codebase and environment files to verify
    zero server secrets (SHOPKEEPER_AUTH_TOKEN, DATABASE_URL, GNANI_API_KEY)
    are exposed via NEXT_PUBLIC_ variables.
    """
    frontend_dir = ROOT / "frontend"
    env_local = frontend_dir / ".env.local"
    env_example = frontend_dir / ".env.example"

    forbidden_tokens = [
        "demo-shopkeeper-secret-key",
        "vach_",
        "postgresql://",
        "postgres@",
    ]

    # Check env files
    for p in [env_local, env_example]:
        if p.exists():
            content = p.read_text(encoding="utf-8")
            for forbidden in forbidden_tokens:
                assert forbidden not in content, f"Leaked forbidden secret in {p}: {forbidden}"

    # Verify NEXT_PUBLIC_ in frontend/ only contains safe variables
    for tsx_file in frontend_dir.glob("**/*.ts*"):
        if "node_modules" in str(tsx_file) or ".next" in str(tsx_file):
            continue
        text = tsx_file.read_text(encoding="utf-8")
        if "process.env.NEXT_PUBLIC_" in text:
            # Check what NEXT_PUBLIC vars are accessed
            import re
            matches = re.findall(r"NEXT_PUBLIC_[A-Z0-9_]+", text)
            for m in matches:
                assert m in ("NEXT_PUBLIC_API_BASE_URL", "NEXT_PUBLIC_STORE_ID"), (
                    f"Unexpected NEXT_PUBLIC variable accessed in {tsx_file}: {m}"
                )


def test_voice_turn_tts_failure_preserves_order_state(pg_client):
    """
    TASK 8: If Timbre TTS service fails (e.g. network timeout or service error),
    the order turn must NOT crash or lose session cart state.
    It returns assistant_text with audio_status='failed' and audio_url=None.
    """
    store_id = "STORE001"
    # Create session
    sess_resp = pg_client.post("/api/v1/sessions", json={"store_id": store_id})
    assert sess_resp.status_code in (200, 201)
    session_id = sess_resp.json()["session_id"]

    # Mock Timbre TTS service to raise an exception or return failure
    from backend.app.services.text_to_speech import TimbreTTSService
    from backend.app.services.speech_to_text import PrismaSTTService, STTResult

    with patch.object(TimbreTTSService, "synthesize", side_effect=RuntimeError("Gnani Timbre TTS timed out")):
        # Call voice turn with a sample wav
        sample_audio = ROOT / "tests" / "voice" / "sample_audio.wav"
        if not sample_audio.exists():
            # Create a minimal 1-second 16kHz mono PCM wav in-memory
            import io, wave
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b"\x00\x00" * 16000)
            audio_bytes = buf.getvalue()
        else:
            audio_bytes = sample_audio.read_bytes()

        # Mock STT to return valid order intent
        with patch.object(PrismaSTTService, "transcribe", return_value=STTResult(
            success=True,
            transcript="do packet maggi chahiye",
            detected_language="hi",
            latency_ms=120.0
        )):
            resp = pg_client.post(
                f"/api/v1/voice/sessions/{session_id}/turn",
                files={"audio_file": ("test.wav", audio_bytes, "audio/wav")}
            )

            assert resp.status_code == 200
            data = resp.json()
            # Cart is preserved and updated
            assert data["cart"]["item_count"] >= 1
            # Assistant text is provided
            assert len(data["assistant_text"]) > 0
            # Audio status is gracefully marked failed without crashing the session
            assert data["audio_status"] == "failed"
            assert data["audio_url"] is None

    # Verify session detail endpoint confirms items are stored
    detail_resp = pg_client.get(f"/api/v1/sessions/{session_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["item_count"] >= 1
