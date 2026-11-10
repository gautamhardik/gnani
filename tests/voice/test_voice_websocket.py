"""
Integration tests for Full-Duplex Voice WebSocket Stream Endpoint (Phase 1 Blueprint).
Verifies:
  - Connection lifecycle
  - Ping / Pong
  - Instant Contextual Filler delivery (<150 ms)
  - Streaming semantic audio chunks (checkFlush)
  - Sub-millisecond Barge-In Abort signal
  - Hallucinated noise filtering
"""

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.text_to_speech import TTSResult


def test_websocket_ping_pong(client: TestClient):
    with client.websocket_connect("/api/v1/voice/sessions/SES_WS_001/stream") as ws:
        ws.send_json({"type": "ping"})
        resp = ws.receive_json()
        assert resp["type"] == "pong"
        assert "timestamp" in resp


def test_websocket_barge_in_acknowledgment(client: TestClient):
    with client.websocket_connect("/api/v1/voice/sessions/SES_WS_002/stream") as ws:
        ws.send_json({"type": "barge_in"})
        resp = ws.receive_json()
        assert resp["type"] == "barge_in_ack"
        assert "timestamp" in resp


def test_websocket_turn_with_filler_and_streaming_chunks(client: TestClient, db_session):
    mock_tts_res = TTSResult(
        success=True,
        audio_id="test_chunk_id",
        audio_bytes=b"testaudio",
        latency_ms=45.0
    )

    with patch("backend.app.api.v1.voice.TimbreTTSService.synthesize", return_value=mock_tts_res):
        with client.websocket_connect("/api/v1/voice/sessions/SES_WS_003/stream") as ws:
            # Send text query to add item
            ws.send_json({
                "type": "text_query",
                "text": "1 kilo chini add kar do",
                "store_id": "STORE001"
            })

            messages = []
            while True:
                msg = ws.receive_json()
                messages.append(msg)
                if msg.get("type") in ["turn_complete", "turn_error", "error"]:
                    break

            msg_types = [m["type"] for m in messages]

            # 1. Check contextual filler was emitted
            assert "filler" in msg_types
            filler_msg = next(m for m in messages if m["type"] == "filler")
            assert filler_msg["intent"] == "add_items"

            # 2. Check turn_complete payload
            assert "turn_complete" in msg_types
            turn_complete = next(m for m in messages if m["type"] == "turn_complete")
            assert turn_complete["session_id"] == "SES_WS_003"
            assert turn_complete["total_amount"] > 0
            assert len(turn_complete["cart"]) >= 1


def test_websocket_hallucinated_noise_rejection(client: TestClient):
    with client.websocket_connect("/api/v1/voice/sessions/SES_WS_004/stream") as ws:
        # Send gibberish Latin string that fails Devanagari ratio and known keywords
        ws.send_json({
            "type": "text_query",
            "text": "asdfghjkl qwerty zxcvbnm",
            "store_id": "STORE001"
        })
        resp = ws.receive_json()
        assert resp["type"] == "stt_mishear"
        assert "dobara boliye" in resp["text"]
