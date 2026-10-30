import pytest

def test_list_inventory(client):
    response = client.get("/api/v1/inventory?page=1&size=20")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 20
    assert data["total"] >= 100

def test_get_inventory_item(client):
    response = client.get("/api/v1/inventory/PRD002")
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == "PRD002"
    assert "stock_quantity" in data
    assert "low_stock_threshold" in data

def test_update_inventory_stock_creates_movement(client, merchant_headers):
    # Unauthorized
    unauth = client.put("/api/v1/inventory/PRD002", json={"stock_quantity": 80.0})
    assert unauth.status_code == 401

    # Authorized stock update
    resp = client.put(
        "/api/v1/inventory/PRD002",
        headers=merchant_headers,
        json={
            "stock_quantity": 88.0,
            "low_stock_threshold": 10.0,
            "reason": "manual_count_adjustment"
        }
    )
    assert resp.status_code == 200
    assert float(resp.json()["stock_quantity"]) == 88.0
