import pytest
from decimal import Decimal

def test_list_products_pagination(client):
    response = client.get("/api/v1/products?page=1&size=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 10
    assert data["total"] >= 100
    assert data["has_more"] is True

def test_search_products_canonical_and_alias(client):
    # 1. Search canonical brand / name
    res1 = client.get("/api/v1/products/search?q=Maggi")
    assert res1.status_code == 200
    items1 = res1.json()
    assert len(items1) > 0
    assert any("Maggi" in item["name"] for item in items1)

    # 2. Search vernacular alias: 'atta' or 'chini' or 'doodh'
    res2 = client.get("/api/v1/products/search?q=chini")
    assert res2.status_code == 200
    items2 = res2.json()
    assert len(items2) > 0
    assert any("Sugar" in item["name"] or item.get("matched_alias") for item in items2)

def test_get_product_by_id(client):
    response = client.get("/api/v1/products/PRD001")
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == "PRD001"
    assert "inventory" in data
    assert data["inventory"]["stock_quantity"] is not None
    assert "aliases" in data

def test_get_nonexistent_product_returns_404(client):
    response = client.get("/api/v1/products/PRD_NON_EXISTENT")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_merchant_create_product_protected(client, merchant_headers):
    # Unauthorized attempt
    unauth_resp = client.post("/api/v1/products", json={
        "sku": "NEW-PROD-01",
        "name": "New Tea",
        "category": "Beverages",
        "sale_unit": "packet",
        "pack_size": 1.0,
        "pack_size_unit": "packet",
        "price_inr": 120.0
    })
    assert unauth_resp.status_code == 401

    # Authorized attempt
    auth_resp = client.post(
        "/api/v1/products",
        headers=merchant_headers,
        json={
            "sku": "NEW-PROD-01",
            "name": "Tata Tea Premium",
            "brand": "Tata",
            "category": "Beverages",
            "sale_unit": "packet",
            "pack_size": 500,
            "pack_size_unit": "g",
            "price_inr": 210.0,
            "initial_stock": 25.0,
            "low_stock_threshold": 5.0,
            "aliases": ["tata chai", "patti"]
        }
    )
    assert auth_resp.status_code == 201
    created = auth_resp.json()
    assert created["name"] == "Tata Tea Premium"
    assert float(created["inventory"]["stock_quantity"]) == 25.0
    assert len(created["aliases"]) == 2

def test_merchant_update_and_deactivate_product(client, merchant_headers):
    # Update price
    update_resp = client.put(
        "/api/v1/products/PRD001",
        headers=merchant_headers,
        json={"price_inr": 59.50}
    )
    assert update_resp.status_code == 200
    assert float(update_resp.json()["price_inr"]) == 59.50

    # Deactivate
    deact_resp = client.delete(
        "/api/v1/products/PRD001",
        headers=merchant_headers
    )
    assert deact_resp.status_code == 200

    # Verify inactive
    get_resp = client.get("/api/v1/products/PRD001")
    assert get_resp.json()["is_active"] is False
