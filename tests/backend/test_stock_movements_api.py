"""
DukaanSaathi — Stock Movements Audit Feed API Tests (Phase 6)
Verifies protected audit trail of all inventory alterations, filtering, and authorization.
"""

import pytest
from backend.app.core.config import settings


def test_stock_movements_requires_auth(client):
    response = client.get("/api/v1/inventory/movements")
    assert response.status_code == 401


def test_stock_movements_list_and_filter(client, merchant_headers):
    # Make a manual stock update to ensure there's at least one movement
    update_resp = client.put(
        "/api/v1/inventory/PRD005",
        headers=merchant_headers,
        json={"stock_quantity": 45.0, "reason": "Restocked test batch"}
    )
    assert update_resp.status_code == 200

    # Query movements
    response = client.get("/api/v1/inventory/movements?product_id=PRD005", headers=merchant_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    recent = data["items"][0]
    assert recent["product_id"] == "PRD005"
    assert "reason" in recent
    assert "change_quantity" in recent
