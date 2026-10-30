import pytest
from decimal import Decimal
from backend.app.models import StoreInventory, StockMovement, Order

def test_critical_business_rule_order_creation_does_not_deduct_stock(client, db_session, merchant_headers):
    """
    CRITICAL BUSINESS RULE:
    1. Customer confirms cart -> pending order created.
    2. Stock remains strictly UNDEDUCTED until shopkeeper explicitly accepts.
    3. Shopkeeper acceptance atomically verifies and deducts stock.
    """
    # Baseline stock check for PRD003 and PRD004
    inv3 = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD003").first()
    inv4 = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD004").first()
    stock3_initial = inv3.stock_quantity
    stock4_initial = inv4.stock_quantity

    order_payload = {
        "store_id": "STORE001",
        "items": [
            {"product_id": "PRD003", "quantity": 2.0},
            {"product_id": "PRD004", "quantity": 3.0}
        ]
    }

    # Step 1: Customer confirms order
    create_resp = client.post("/api/v1/orders", json=order_payload)
    assert create_resp.status_code == 201
    order_data = create_resp.json()
    order_id = order_data["order_id"]
    assert order_data["status"] == "pending"
    assert len(order_data["items"]) == 2
    assert float(order_data["total_amount"]) > 0

    # Step 2: Verify stock is STILL UNTOUCHED in database
    db_session.expire_all()
    inv3_after_create = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD003").first()
    inv4_after_create = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD004").first()
    assert inv3_after_create.stock_quantity == stock3_initial, "Stock was prematurely deducted upon pending order creation!"
    assert inv4_after_create.stock_quantity == stock4_initial, "Stock was prematurely deducted upon pending order creation!"

    # Step 3: Shopkeeper accepts order
    accept_resp = client.post(f"/api/v1/orders/{order_id}/accept", headers=merchant_headers)
    assert accept_resp.status_code == 200
    accepted_order = accept_resp.json()
    assert accepted_order["status"] == "accepted"

    # Step 4: Verify stock is NOW decremented atomically
    db_session.expire_all()
    inv3_after_accept = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD003").first()
    inv4_after_accept = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD004").first()
    assert inv3_after_accept.stock_quantity == stock3_initial - Decimal(2.0)
    assert inv4_after_accept.stock_quantity == stock4_initial - Decimal(3.0)

    # Step 5: Verify stock movements audit log
    movements = db_session.query(StockMovement).filter(StockMovement.order_id == order_id).all()
    assert len(movements) == 2
    assert all(m.reason == "merchant_order_accepted" for m in movements)
    assert all(m.change_quantity < 0 for m in movements)


def test_shopkeeper_acceptance_fails_atomically_if_stock_insufficient(client, db_session, merchant_headers):
    """
    If stock is modified between customer placement and shopkeeper acceptance,
    acceptance must fail atomically and deduct ZERO stock.
    """
    inv = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD005").first()
    initial_stock = inv.stock_quantity

    # Place order for 5 units
    order_resp = client.post("/api/v1/orders", json={
        "store_id": "STORE001",
        "items": [{"product_id": "PRD005", "quantity": 5.0}]
    })
    assert order_resp.status_code == 201
    order_id = order_resp.json()["order_id"]

    # Concurrently reduce inventory to 2 units (insufficient for 5 units)
    inv.stock_quantity = Decimal(2.0)
    db_session.commit()

    # Shopkeeper attempts to accept
    accept_resp = client.post(f"/api/v1/orders/{order_id}/accept", headers=merchant_headers)
    assert accept_resp.status_code in (400, 409)
    err_detail = accept_resp.json()["detail"].lower()
    assert "insufficient stock" in err_detail

    # Verify atomic rollback: stock remains 2.0 (not negative), order remains pending
    db_session.expire_all()
    inv_final = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD005").first()
    order_final = db_session.query(Order).filter(Order.order_id == order_id).first()
    assert inv_final.stock_quantity == Decimal(2.0)
    assert order_final.status == "pending"


def test_shopkeeper_rejects_pending_order(client, db_session, merchant_headers):
    """
    Rejection updates status to rejected with reason and touches no stock.
    """
    order_resp = client.post("/api/v1/orders", json={
        "store_id": "STORE001",
        "items": [{"product_id": "PRD006", "quantity": 1.0}]
    })
    order_id = order_resp.json()["order_id"]

    reject_resp = client.post(
        f"/api/v1/orders/{order_id}/reject",
        headers=merchant_headers,
        json={"reason": "Store closed for Diwali festival"}
    )
    assert reject_resp.status_code == 200
    rejected_order = reject_resp.json()
    assert rejected_order["status"] == "rejected"
    assert rejected_order["rejection_reason"] == "Store closed for Diwali festival"


def test_order_validation_empty_cart_and_negative_quantities(client):
    # Empty cart
    resp1 = client.post("/api/v1/orders", json={"items": []})
    assert resp1.status_code == 422 or resp1.status_code == 400

    # Non-existent product
    resp2 = client.post("/api/v1/orders", json={
        "items": [{"product_id": "NON_EXISTENT_SKU", "quantity": 1.0}]
    })
    assert resp2.status_code == 404
