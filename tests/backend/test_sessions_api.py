"""
DukaanSaathi — Customer Sessions API Tests
"""

import pytest

def test_create_and_get_session(client):
    """Verifies customer session creation and state retrieval."""
    # 1. Create session
    create_resp = client.post("/api/v1/sessions", json={"store_id": "STORE001"})
    assert create_resp.status_code == 201
    sess_data = create_resp.json()
    session_id = sess_data["session_id"]
    assert session_id.startswith("SESS")
    assert sess_data["status"] == "active"
    assert sess_data["current_cart"] == []

    # 2. Get session details
    get_resp = client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["session_id"] == session_id
    assert detail["item_count"] == 0
    assert float(detail["total_amount"]) == 0.0

def test_update_and_remove_cart_item(client):
    """Verifies manual cart modification via backend authoritative APIs."""
    # 1. Create session
    create_resp = client.post("/api/v1/sessions", json={"store_id": "STORE001"})
    session_id = create_resp.json()["session_id"]

    # 2. Add product PRD001 (Loose Wheat Flour 42.00 INR/kg) quantity 3
    put_resp = client.put(
        f"/api/v1/sessions/{session_id}/cart/items/PRD001",
        json={"quantity": 3.0}
    )
    assert put_resp.status_code == 200
    cart_data = put_resp.json()
    assert cart_data["item_count"] == 1
    assert cart_data["current_cart"][0]["product_id"] == "PRD001"
    assert cart_data["current_cart"][0]["quantity"] == 3.0
    # Price is 42.00, subtotal 126.00
    assert float(cart_data["total_amount"]) == 126.0

    # 3. Update quantity to 5
    put_resp2 = client.put(
        f"/api/v1/sessions/{session_id}/cart/items/PRD001",
        json={"quantity": 5.0}
    )
    assert put_resp2.status_code == 200
    assert float(put_resp2.json()["total_amount"]) == 210.0

    # 4. Remove item
    del_resp = client.delete(f"/api/v1/sessions/{session_id}/cart/items/PRD001")
    assert del_resp.status_code == 200
    del_data = del_resp.json()
    assert del_data["item_count"] == 0
    assert float(del_data["total_amount"]) == 0.0

def test_cart_item_stock_validation(client):
    """Verifies cart rejection when requested quantity exceeds available stock."""
    create_resp = client.post("/api/v1/sessions", json={"store_id": "STORE001"})
    session_id = create_resp.json()["session_id"]

    # Request impossible quantity 99999
    put_resp = client.put(
        f"/api/v1/sessions/{session_id}/cart/items/PRD001",
        json={"quantity": 99999.0}
    )
    assert put_resp.status_code == 400
    assert "Insufficient stock" in put_resp.json()["detail"]
