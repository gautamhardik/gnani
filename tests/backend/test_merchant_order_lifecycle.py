"""
DukaanSaathi — Merchant Order Lifecycle & State Machine Tests (Phase 6)
Verifies full operational order flow, status transitions, atomic stock deduction,
compensating inventory restoration upon cancellation, and live overview metrics.
"""

import pytest
from decimal import Decimal
from backend.app.core.config import settings
from backend.app.models import StoreInventory


def test_merchant_overview_live_metrics(client, merchant_headers):
    response = client.get("/api/v1/merchant/overview", headers=merchant_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["store_id"] == settings.DEMO_STORE_ID
    assert "store_name" in data
    assert isinstance(data["pending_orders_count"], int)
    assert isinstance(data["today_orders_count"], int)
    assert isinstance(data["completed_orders_count"], int)
    assert float(data["total_sales_inr"]) >= 0.0
    assert isinstance(data["low_stock_products_count"], int)
    assert isinstance(data["out_of_stock_count"], int)
    assert isinstance(data["total_products_count"], int)
    assert isinstance(data["recent_orders"], list)


def test_order_full_lifecycle_progression(client, merchant_headers, db_session):
    """
    Tests: pending -> accepted (stock deducted) -> preparing -> ready -> completed
    """
    # 1. Baseline stock check for PRD001 (Amul Taaza Toned Milk 500ml)
    inv1 = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD001").first()
    stock_before = float(inv1.stock_quantity)

    # 2. Place pending order
    order_payload = {
        "store_id": "STORE001",
        "customer_name": "Rohan Merchant Test",
        "customer_phone": "9876543210",
        "notes": "Test order for lifecycle",
        "items": [
            {"product_id": "PRD001", "quantity": 2.0}
        ]
    }
    order_create_resp = client.post("/api/v1/orders", json=order_payload)
    assert order_create_resp.status_code == 201
    order_data = order_create_resp.json()
    order_id = order_data["order_id"]
    assert order_data["status"] == "pending"

    # Invariant: stock must NOT be deducted on pending creation
    db_session.expire_all()
    inv_pending = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD001").first()
    assert float(inv_pending.stock_quantity) == stock_before

    # 3. Accept order (protected)
    accept_resp = client.post(f"/api/v1/orders/{order_id}/accept", headers=merchant_headers)
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "accepted"

    # Invariant: stock deducted upon acceptance
    db_session.expire_all()
    inv_accepted = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD001").first()
    assert float(inv_accepted.stock_quantity) == stock_before - 2.0

    # 4. Transition accepted -> preparing
    prep_resp = client.post(
        f"/api/v1/orders/{order_id}/status",
        headers=merchant_headers,
        json={"status": "preparing", "notes": "Order packed into bag"}
    )
    assert prep_resp.status_code == 200
    assert prep_resp.json()["status"] == "preparing"

    # 5. Transition preparing -> ready
    ready_resp = client.post(
        f"/api/v1/orders/{order_id}/status",
        headers=merchant_headers,
        json={"status": "ready", "notes": "Ready on pickup counter"}
    )
    assert ready_resp.status_code == 200
    assert ready_resp.json()["status"] == "ready"

    # 6. Transition ready -> completed
    comp_resp = client.post(
        f"/api/v1/orders/{order_id}/status",
        headers=merchant_headers,
        json={"status": "completed", "notes": "Customer picked up items"}
    )
    assert comp_resp.status_code == 200
    assert comp_resp.json()["status"] == "completed"

    # 7. Invalid transition check: completed cannot transition to preparing
    inv_trans = client.post(
        f"/api/v1/orders/{order_id}/status",
        headers=merchant_headers,
        json={"status": "preparing"}
    )
    assert inv_trans.status_code == 400


def test_order_cancellation_restores_inventory(client, merchant_headers, db_session):
    """
    Tests: pending -> accepted (stock deducted) -> cancelled (stock restored)
    """
    inv2 = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD002").first()
    stock_start = float(inv2.stock_quantity)

    order_payload = {
        "store_id": "STORE001",
        "customer_name": "Ananya Cancel Test",
        "customer_phone": "9811122233",
        "items": [
            {"product_id": "PRD002", "quantity": 3.0}
        ]
    }
    order_resp = client.post("/api/v1/orders", json=order_payload)
    assert order_resp.status_code == 201
    order_id = order_resp.json()["order_id"]

    # Accept order
    client.post(f"/api/v1/orders/{order_id}/accept", headers=merchant_headers)
    db_session.expire_all()
    inv_after_accept = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD002").first()
    assert float(inv_after_accept.stock_quantity) == stock_start - 3.0

    # Cancel order via merchant transition
    cancel_resp = client.post(
        f"/api/v1/orders/{order_id}/status",
        headers=merchant_headers,
        json={"status": "cancelled", "notes": "Customer requested cancellation"}
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # Verify inventory is restored
    db_session.expire_all()
    inv_after_cancel = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD002").first()
    assert float(inv_after_cancel.stock_quantity) == stock_start


def test_order_rejection_flow_zero_stock_deduction(client, merchant_headers, db_session):
    """
    Tests: pending -> rejected (stock never deducted)
    """
    inv5 = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD005").first()
    stock_start = float(inv5.stock_quantity)

    order_payload = {
        "store_id": "STORE001",
        "customer_name": "Dev Reject Test",
        "customer_phone": "9988776655",
        "items": [
            {"product_id": "PRD005", "quantity": 1.0}
        ]
    }
    order_resp = client.post("/api/v1/orders", json=order_payload)
    assert order_resp.status_code == 201
    order_id = order_resp.json()["order_id"]

    # Reject order
    reject_resp = client.post(
        f"/api/v1/orders/{order_id}/reject",
        headers=merchant_headers,
        json={"reason": "Shop closed for lunch"}
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"

    # Stock must remain unaffected
    db_session.expire_all()
    inv_after_reject = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD005").first()
    assert float(inv_after_reject.stock_quantity) == stock_start
