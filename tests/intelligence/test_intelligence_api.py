"""
DukaanSaathi — Intelligence API Integration Tests
Tests HTTP endpoints under /api/v1/intelligence.
"""

import pytest
from backend.app.models import OrderSession

def test_process_turn_creates_session_and_adds_item(client, db_session):
    payload = {
        "utterance": "Mujhe ek kilo aata chahiye.",
        "store_id": "STORE001"
    }
    response = client.post("/api/v1/intelligence/process-turn", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["session_id"].startswith("SESS")
    assert data["action"]["action"] == "add_items"
    assert len(data["cart"]) == 1
    assert data["cart"][0]["product_id"] == "PRD001"
    assert float(data["cart"][0]["quantity"]) == 1.0

    # Verify session persisted in DB
    sess = db_session.query(OrderSession).filter(OrderSession.session_id == data["session_id"]).first()
    assert sess is not None
    assert len(sess.current_cart) == 1

def test_process_turn_multi_turn_persists_session(client, db_session):
    session_id = "SESS_TEST_MULTI_TURN"

    # Turn 1: Add Atta
    r1 = client.post("/api/v1/intelligence/process-turn", json={
        "session_id": session_id,
        "utterance": "Ek kilo aata de do.",
        "store_id": "STORE001"
    })
    assert r1.status_code == 200
    assert len(r1.json()["cart"]) == 1

    # Turn 2: Add 2 Maggi
    r2 = client.post("/api/v1/intelligence/process-turn", json={
        "session_id": session_id,
        "utterance": "Aur do packet Maggi add karo.",
        "store_id": "STORE001"
    })
    assert r2.status_code == 200
    cart_r2 = r2.json()["cart"]
    assert len(cart_r2) == 2
    pids = [it["product_id"] for it in cart_r2]
    assert "PRD001" in pids
    assert "PRD041" in pids

    # Turn 3: Confirm Order
    r3 = client.post("/api/v1/intelligence/process-turn", json={
        "session_id": session_id,
        "utterance": "Haan, order confirm kar do.",
        "store_id": "STORE001"
    })
    assert r3.status_code == 200
    assert r3.json()["state"] == "ORDER_PLACED"

    # Check database session status
    db_session.expire_all()
    sess = db_session.query(OrderSession).filter(OrderSession.session_id == session_id).first()
    assert sess.status == "confirmed"

def test_process_turn_nonexistent_store_returns_404(client):
    payload = {
        "utterance": "Ek kilo aata chahiye.",
        "store_id": "STORE_INVALID_999"
    }
    response = client.post("/api/v1/intelligence/process-turn", json=payload)
    assert response.status_code == 404

