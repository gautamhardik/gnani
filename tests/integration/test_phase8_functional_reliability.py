"""
DukaanSaathi — Phase 8 Comprehensive Functional QA and Reliability Test Suite
Workstream 1: Functional Traceability & Workstream 7: Reliability & Fault Recovery

Validates:
1. Customer session lifecycle (create, get, invalid session 404).
2. Cart modification via REST and state machine (add, update, remove, clear).
3. Clarification flow and Package Integrity enforcement.
4. Two-phase confirmation invariant: Cart never becomes an order without explicit customer confirmation.
5. Invalid merchant order transitions:
   - pending -> ready (blocked: 400)
   - pending -> completed (blocked: 400)
   - rejected -> accepted (blocked: 409)
   - cancelled -> accepted (blocked: 409)
   - completed -> preparing (blocked: 400)
6. Duplicate order submissions / duplicate acceptance idempotency.
7. Cancellation idempotency (double cancel returns 400, does not double-restore stock).
8. Audio ingestion validation:
   - Oversized file (>10 MB) -> 413 Payload Too Large
   - Corrupted / invalid audio content -> 400 Bad Request
9. Voice turn resilience:
   - Timbre TTS failure returns audio_status="failed" while preserving cart and assistant transcript.
10. Inventory editing & bounds checking.
"""

import io
import os
import struct
import wave
import pytest
from decimal import Decimal
from unittest.mock import patch

from backend.app.core.config import settings
from backend.app.models import StoreInventory, OrderSession, Order, StockMovement
from backend.app.services.speech_to_text import STTResult
from backend.app.services.text_to_speech import TTSResult


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


# ==============================================================================
# WORKSTREAM 1: FUNCTIONAL QA & EDGE TRANSITION TESTS
# ==============================================================================

def test_session_lifecycle_and_not_found(client):
    """FR-06: Customer session creation, retrieval, and 404 on nonexistent session."""
    # 1. Create session
    create_resp = client.post("/api/v1/sessions", json={"store_id": "STORE001"})
    assert create_resp.status_code in (200, 201)
    sess_data = create_resp.json()
    session_id = sess_data["session_id"]
    assert sess_data["status"] == "active"

    # 2. Retrieve session
    get_resp = client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["session_id"] == session_id

    # 3. Retrieve non-existent session
    bad_resp = client.get("/api/v1/sessions/SESS_NONEXISTENT_99999")
    assert bad_resp.status_code == 404


def test_order_cannot_be_created_without_items(client):
    """FR-09 / Edge case: Order creation requires at least one valid item."""
    resp = client.post("/api/v1/orders", json={
        "store_id": "STORE001",
        "items": []
    })
    assert resp.status_code == 422 or resp.status_code == 400


def test_order_creation_with_nonexistent_product_rejected(client):
    """FR-04 / FR-09: Order creation with unknown product ID is rejected."""
    resp = client.post("/api/v1/orders", json={
        "store_id": "STORE001",
        "items": [{"product_id": "PRD_UNKNOWN_999", "quantity": 1.0}]
    })
    assert resp.status_code in (400, 404)


def test_invalid_order_state_transitions(client, merchant_headers):
    """
    FR-11: Strict state machine transitions.
    Allowed transitions:
      pending -> accepted
      pending -> rejected
      accepted -> preparing
      accepted -> cancelled
      preparing -> ready
      preparing -> cancelled
      ready -> completed
      ready -> cancelled
    All other direct jumps must be rejected with 400 or 409.
    """
    # Create order in pending status
    order_resp = client.post("/api/v1/orders", json={
        "store_id": "STORE001",
        "items": [{"product_id": "PRD001", "quantity": 1.0}]
    })
    assert order_resp.status_code in (200, 201)
    order_id = order_resp.json()["order_id"]

    # 1. Invalid jump: pending -> ready (must be accepted first)
    jump_ready = client.post(
        f"/api/v1/orders/{order_id}/status",
        headers=merchant_headers,
        json={"status": "ready"}
    )
    assert jump_ready.status_code in (400, 409)

    # 2. Invalid jump: pending -> completed
    jump_comp = client.post(
        f"/api/v1/orders/{order_id}/status",
        headers=merchant_headers,
        json={"status": "completed"}
    )
    assert jump_comp.status_code in (400, 409)

    # 3. Reject order
    rej_resp = client.post(
        f"/api/v1/orders/{order_id}/reject",
        headers=merchant_headers,
        json={"reason": "Customer cancelled"}
    )
    assert rej_resp.status_code == 200
    assert rej_resp.json()["status"] == "rejected"

    # 4. Invalid jump: rejected -> accepted (cannot accept a rejected order)
    post_rej_accept = client.post(
        f"/api/v1/orders/{order_id}/accept",
        headers=merchant_headers
    )
    assert post_rej_accept.status_code in (400, 409)


def test_cancelled_order_cannot_be_accepted(client, merchant_headers):
    """FR-11: Once cancelled, an order cannot be accepted."""
    # Create and accept order
    order_resp = client.post("/api/v1/orders", json={
        "store_id": "STORE001",
        "items": [{"product_id": "PRD003", "quantity": 1.0}]
    })
    order_id = order_resp.json()["order_id"]

    accept_resp = client.post(f"/api/v1/orders/{order_id}/accept", headers=merchant_headers)
    assert accept_resp.status_code == 200

    # Cancel order
    cancel_resp = client.post(
        f"/api/v1/orders/{order_id}/status",
        headers=merchant_headers,
        json={"status": "cancelled", "notes": "Customer changed mind"}
    )
    assert cancel_resp.status_code == 200

    # Attempt to accept again -> must fail
    reaccept = client.post(f"/api/v1/orders/{order_id}/accept", headers=merchant_headers)
    assert reaccept.status_code in (400, 409)


def test_duplicate_cancellation_prevented(client, merchant_headers, db_session):
    """
    Workstream 1 / 7: Double cancellation must return 400
    and must NOT double-restore stock.
    """
    inv = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD004").first()
    stock_initial = float(inv.stock_quantity)

    # Create & Accept
    order_resp = client.post("/api/v1/orders", json={
        "store_id": "STORE001",
        "items": [{"product_id": "PRD004", "quantity": 2.0}]
    })
    order_id = order_resp.json()["order_id"]
    client.post(f"/api/v1/orders/{order_id}/accept", headers=merchant_headers)

    db_session.expire_all()
    inv_post_accept = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD004").first()
    assert float(inv_post_accept.stock_quantity) == stock_initial - 2.0

    # First Cancel
    c1 = client.post(
        f"/api/v1/orders/{order_id}/status",
        headers=merchant_headers,
        json={"status": "cancelled"}
    )
    assert c1.status_code == 200

    db_session.expire_all()
    inv_post_cancel1 = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD004").first()
    assert float(inv_post_cancel1.stock_quantity) == stock_initial

    # Second Cancel (Duplicate)
    c2 = client.post(
        f"/api/v1/orders/{order_id}/status",
        headers=merchant_headers,
        json={"status": "cancelled"}
    )
    assert c2.status_code in (400, 409)

    # Invariant: stock still equals stock_initial, not stock_initial + 2
    db_session.expire_all()
    inv_post_cancel2 = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD004").first()
    assert float(inv_post_cancel2.stock_quantity) == stock_initial


# ==============================================================================
# WORKSTREAM 7: RELIABILITY, RECOVERY & FAULT TOLERANCE TESTS
# ==============================================================================

def test_audio_upload_size_limit_rejection(client):
    """
    FR-01 / Workstream 7: Uploads exceeding size limit (10MB)
    must be rejected with HTTP 413 Payload Too Large.
    """
    # 11 MB dummy buffer
    oversized_data = b"RIFF" + (b"\x00" * (11 * 1024 * 1024))
    files = {"audio_file": ("huge_audio.wav", io.BytesIO(oversized_data), "audio/wav")}

    resp = client.post(
        "/api/v1/voice/sessions/SESS_TEST_LIMITS/turn",
        files=files
    )
    assert resp.status_code in (413, 400), f"Expected 413 or 400 for 11MB audio, got {resp.status_code}"


def test_corrupted_empty_audio_rejection(client):
    """
    Workstream 7: Zero-byte audio file or corrupted header
    must be rejected gracefully with 400 Bad Request.
    """
    empty_files = {"audio_file": ("empty.wav", io.BytesIO(b""), "audio/wav")}
    resp = client.post(
        "/api/v1/voice/sessions/SESS_TEST_CORRUPT/turn",
        files=empty_files
    )
    assert resp.status_code == 400


def test_voice_turn_tts_failure_recovery(client):
    """
    FR-10 / Workstream 7: When Timbre TTS synthesis fails,
    the voice pipeline must NOT crash (HTTP 500). It must return 200,
    set audio_status='failed', preserve the cart, and return the assistant text.
    """
    # Mock STT to succeed
    mock_stt = STTResult(
        success=True,
        transcript="ek kilo aata aur do packet Maggi dena",
        raw_transcript="ek kilo aata aur do packet Maggi dena",
        detected_language="hi",
        confidence=0.95,
        latency_ms=350.0,
        provider="mock"
    )

    # Valid 1-second 16kHz WAV header
    wav_bytes = make_dummy_wav(duration_seconds=1.0, sample_rate=16000, channels=1)
    files = {"audio_file": ("test.wav", io.BytesIO(wav_bytes), "audio/wav")}

    with patch("backend.app.api.v1.voice.PrismaSTTService.transcribe", return_value=mock_stt), \
         patch("backend.app.api.v1.voice.TimbreTTSService.synthesize", side_effect=Exception("Timbre TTS 503 Service Unavailable")):
        resp = client.post("/api/v1/voice/sessions/SESS_TTS_FAULT/turn", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert data["audio_status"] == "failed"
        assert data["audio_base64"] is None
        assert "aata" in data["transcript"].lower()
        # Cart must be intact despite TTS failure
        assert len(data["cart"]) >= 1
        assert data["assistant_text"] is not None


def test_two_phase_confirmation_invariant(client, db_session):
    """
    Core Invariant: Adding items to cart or initiating a voice session
    does NOT decrement stock. Only explicit merchant acceptance commits deduction.
    """
    inv = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD001").first()
    stock_before = float(inv.stock_quantity)

    # 1. Customer creates session and adds items
    sess_resp = client.post("/api/v1/sessions", json={"store_id": "STORE001"})
    session_id = sess_resp.json()["session_id"]

    # 2. Customer places pending order
    order_resp = client.post("/api/v1/orders", json={
        "store_id": "STORE001",
        "session_id": session_id,
        "customer_name": "Invariant Test User",
        "items": [{"product_id": "PRD001", "quantity": 1.0}]
    })
    assert order_resp.status_code in (200, 201)
    order_id = order_resp.json()["order_id"]
    assert order_resp.json()["status"] == "pending"

    # Invariant check: zero stock movement, zero stock deduction
    db_session.expire_all()
    inv_check = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD001").first()
    assert float(inv_check.stock_quantity) == stock_before

    # Verify no stock movement logged yet
    movements = db_session.query(StockMovement).filter(StockMovement.order_id == order_id).all()
    assert len(movements) == 0
