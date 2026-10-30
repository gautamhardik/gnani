"""
DukaanSaathi — Phase 7 Full System End-to-End Workflows on Real PostgreSQL
Tests complete customer and merchant lifecycles against real PostgreSQL 16.6.
"""

from decimal import Decimal
import pytest
from backend.app.models import StoreInventory, Order, StockMovement, OrderSession

def test_full_customer_workflow_creates_pending_order_with_zero_stock_deduction(pg_client, pg_db):
    """
    TASK 3 — Customer Workflow:
    1. Session creation.
    2. Add items to cart.
    3. Verify session cart calculation.
    4. Confirm & place order.
    5. INVARIANT: Order is 'pending'; stock is untouched in PostgreSQL.
    """
    store_id = "STORE001"
    product_id = "PRD001"  # Aashirvaad Shudh Chakki Atta 5kg

    # Ensure sufficient stock baseline
    inv_start = pg_db.query(StoreInventory).filter(StoreInventory.product_id == product_id).first()
    assert inv_start is not None
    if inv_start.stock_quantity < Decimal("10.0"):
        inv_start.stock_quantity = Decimal("20.0")
        pg_db.commit()
    stock_start = Decimal(str(inv_start.stock_quantity))

    # 1. Create Customer Session
    sess_resp = pg_client.post("/api/v1/sessions", json={"store_id": store_id})
    assert sess_resp.status_code in (200, 201)
    session_id = sess_resp.json()["session_id"]

    # 2. Add Item to Cart (2 bags)
    cart_resp = pg_client.put(
        f"/api/v1/sessions/{session_id}/cart/items/{product_id}",
        json={"quantity": 2.0}
    )
    assert cart_resp.status_code in (200, 201)
    cart_data = cart_resp.json()
    assert cart_data["item_count"] == 1
    assert float(cart_data["total_amount"]) > 0

    # 3. Submit Customer Order Confirmation
    order_resp = pg_client.post("/api/v1/orders", json={
        "store_id": store_id,
        "session_id": session_id,
        "items": [{"product_id": product_id, "quantity": 2.0}]
    })
    assert order_resp.status_code in (200, 201)
    order_data = order_resp.json()
    order_id = order_data["order_id"]
    assert order_data["status"] == "pending"

    # 4. Critical Invariant Check in Real PostgreSQL
    pg_db.expire_all()
    inv_after_checkout = pg_db.query(StoreInventory).filter(StoreInventory.product_id == product_id).first()
    assert Decimal(str(inv_after_checkout.stock_quantity)) == stock_start, (
        "CRITICAL VIOLATION: Customer order creation must NOT deduct stock before merchant acceptance!"
    )

    # Verify zero stock movements exist for this pending order
    movements = pg_db.query(StockMovement).filter(StockMovement.order_id == order_id).all()
    assert len(movements) == 0, "No stock movements should exist for pending order."


def test_full_merchant_workflow_acceptance_and_lifecycle(pg_client, pg_db, pg_merchant_headers):
    """
    TASK 4 — Merchant Workflow:
    1. Create pending order.
    2. Merchant accepts order -> atomic stock deduction in PostgreSQL + audit row.
    3. Merchant advances: accepted -> preparing -> ready -> completed.
    """
    store_id = "STORE001"
    product_id = "PRD002"  # Fortune Sunlite Refined Sunflower Oil 1L

    inv_start = pg_db.query(StoreInventory).filter(StoreInventory.product_id == product_id).first()
    assert inv_start is not None
    if inv_start.stock_quantity < Decimal("10.0"):
        inv_start.stock_quantity = Decimal("20.0")
        pg_db.commit()
    stock_start = Decimal(str(inv_start.stock_quantity))

    # Place pending order
    order_resp = pg_client.post("/api/v1/orders", json={
        "store_id": store_id,
        "items": [{"product_id": product_id, "quantity": 3.0}]
    })
    assert order_resp.status_code in (200, 201)
    order_id = order_resp.json()["order_id"]

    # Merchant views overview
    overview_resp = pg_client.get("/api/v1/merchant/overview", headers=pg_merchant_headers)
    assert overview_resp.status_code == 200
    assert overview_resp.json()["pending_orders_count"] >= 1

    # Merchant Accepts Order
    accept_resp = pg_client.post(f"/api/v1/orders/{order_id}/accept", headers=pg_merchant_headers)
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "accepted"

    # Verify atomic stock deduction in PostgreSQL
    pg_db.expire_all()
    inv_after_accept = pg_db.query(StoreInventory).filter(StoreInventory.product_id == product_id).first()
    assert Decimal(str(inv_after_accept.stock_quantity)) == stock_start - Decimal("3.0")

    # Verify audit row in stock_movements
    movement = pg_db.query(StockMovement).filter(
        StockMovement.order_id == order_id,
        StockMovement.product_id == product_id
    ).first()
    assert movement is not None
    assert Decimal(str(movement.change_quantity)) == Decimal("-3.0")
    assert movement.reason == "merchant_order_accepted"

    # Advance to preparing
    prep_resp = pg_client.post(
        f"/api/v1/orders/{order_id}/status",
        headers=pg_merchant_headers,
        json={"status": "preparing"}
    )
    assert prep_resp.status_code == 200
    assert prep_resp.json()["status"] == "preparing"

    # Advance to ready
    ready_resp = pg_client.post(
        f"/api/v1/orders/{order_id}/status",
        headers=pg_merchant_headers,
        json={"status": "ready"}
    )
    assert ready_resp.status_code == 200
    assert ready_resp.json()["status"] == "ready"

    # Advance to completed
    comp_resp = pg_client.post(
        f"/api/v1/orders/{order_id}/status",
        headers=pg_merchant_headers,
        json={"status": "completed"}
    )
    assert comp_resp.status_code == 200
    assert comp_resp.json()["status"] == "completed"

    # Verify in PostgreSQL
    pg_db.expire_all()
    final_order = pg_db.query(Order).filter(Order.order_id == order_id).first()
    assert final_order.status == "completed"


def test_merchant_rejection_leaves_stock_untouched(pg_client, pg_db, pg_merchant_headers):
    """
    TASK 5 — Merchant Rejection:
    Order status becomes 'rejected', stock remains completely untouched, no stock movement created.
    """
    store_id = "STORE001"
    product_id = "PRD003"  # India Gate Basmati Rice Feast Rozzana 1kg

    inv_start = pg_db.query(StoreInventory).filter(StoreInventory.product_id == product_id).first()
    assert inv_start is not None
    if inv_start.stock_quantity < Decimal("10.0"):
        inv_start.stock_quantity = Decimal("20.0")
        pg_db.commit()
    stock_start = Decimal(str(inv_start.stock_quantity))

    order_resp = pg_client.post("/api/v1/orders", json={
        "store_id": store_id,
        "items": [{"product_id": product_id, "quantity": 2.0}]
    })
    assert order_resp.status_code in (200, 201)
    order_id = order_resp.json()["order_id"]

    # Reject order
    rejection_reason = "Customer address outside serviceable delivery radius"
    reject_resp = pg_client.post(
        f"/api/v1/orders/{order_id}/reject",
        headers=pg_merchant_headers,
        json={"reason": rejection_reason}
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"
    assert reject_resp.json()["rejection_reason"] == rejection_reason

    # Verify stock in PostgreSQL remains 100% untouched
    pg_db.expire_all()
    inv_after_reject = pg_db.query(StoreInventory).filter(StoreInventory.product_id == product_id).first()
    assert Decimal(str(inv_after_reject.stock_quantity)) == stock_start

    # Verify zero movements created
    movements = pg_db.query(StockMovement).filter(StockMovement.order_id == order_id).all()
    assert len(movements) == 0


def test_order_cancellation_restores_inventory_with_compensating_audit(pg_client, pg_db, pg_merchant_headers):
    """
    TASK 5 — Order Cancellation:
    Cancelling an accepted order restores stock to original level and writes compensating audit row.
    """
    store_id = "STORE001"
    product_id = "PRD004"  # Tata Salt 1kg

    inv_start = pg_db.query(StoreInventory).filter(StoreInventory.product_id == product_id).first()
    assert inv_start is not None
    if inv_start.stock_quantity < Decimal("10.0"):
        inv_start.stock_quantity = Decimal("20.0")
        pg_db.commit()
    stock_start = Decimal(str(inv_start.stock_quantity))

    # Place and accept order (stock deducted)
    order_resp = pg_client.post("/api/v1/orders", json={
        "store_id": store_id,
        "items": [{"product_id": product_id, "quantity": 5.0}]
    })
    assert order_resp.status_code in (200, 201)
    order_id = order_resp.json()["order_id"]
    pg_client.post(f"/api/v1/orders/{order_id}/accept", headers=pg_merchant_headers)

    pg_db.expire_all()
    inv_mid = pg_db.query(StoreInventory).filter(StoreInventory.product_id == product_id).first()
    assert Decimal(str(inv_mid.stock_quantity)) == stock_start - Decimal("5.0")

    # Cancel order
    cancel_resp = pg_client.post(
        f"/api/v1/orders/{order_id}/status",
        headers=pg_merchant_headers,
        json={"status": "cancelled", "notes": "Customer cancelled via phone"}
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # Verify inventory is fully restored in PostgreSQL
    pg_db.expire_all()
    inv_final = pg_db.query(StoreInventory).filter(StoreInventory.product_id == product_id).first()
    assert Decimal(str(inv_final.stock_quantity)) == stock_start

    # Verify compensating stock movement row
    comp_movement = pg_db.query(StockMovement).filter(
        StockMovement.order_id == order_id,
        StockMovement.reason == "order_cancelled_restock"
    ).first()
    assert comp_movement is not None
    assert Decimal(str(comp_movement.change_quantity)) == Decimal("5.0")


def test_cancellation_idempotency_and_invalid_transitions(pg_client, pg_db, pg_merchant_headers):
    """
    TASK 5 — State Machine & Idempotency:
    1. Duplicate cancellation returns 400 Bad Request and does not double-restore stock.
    2. Invalid state transitions (pending -> completed) return 400 Bad Request.
    """
    store_id = "STORE001"
    product_id = "PRD005"  # Maggi 2-Minute Noodles 70g

    inv_start = pg_db.query(StoreInventory).filter(StoreInventory.product_id == product_id).first()
    assert inv_start is not None
    if inv_start.stock_quantity < Decimal("10.0"):
        inv_start.stock_quantity = Decimal("20.0")
        pg_db.commit()
    stock_start = Decimal(str(inv_start.stock_quantity))

    # Place and accept
    order_resp = pg_client.post("/api/v1/orders", json={
        "store_id": store_id,
        "items": [{"product_id": product_id, "quantity": 4.0}]
    })
    assert order_resp.status_code in (200, 201)
    order_id = order_resp.json()["order_id"]
    pg_client.post(f"/api/v1/orders/{order_id}/accept", headers=pg_merchant_headers)

    # Cancel once
    c1 = pg_client.post(
        f"/api/v1/orders/{order_id}/status",
        headers=pg_merchant_headers,
        json={"status": "cancelled"}
    )
    assert c1.status_code == 200

    # Cancel a second time (MUST FAIL and NOT double-restore stock)
    c2 = pg_client.post(
        f"/api/v1/orders/{order_id}/status",
        headers=pg_merchant_headers,
        json={"status": "cancelled"}
    )
    assert c2.status_code == 400
    assert "invalid status transition" in c2.json()["detail"].lower()

    # Stock must be exactly stock_start (not stock_start + 4)
    pg_db.expire_all()
    inv_final = pg_db.query(StoreInventory).filter(StoreInventory.product_id == product_id).first()
    assert Decimal(str(inv_final.stock_quantity)) == stock_start

    # Test illegal transition: pending directly to completed
    order2 = pg_client.post("/api/v1/orders", json={
        "store_id": store_id,
        "items": [{"product_id": product_id, "quantity": 1.0}]
    }).json()
    bad_transition = pg_client.post(
        f"/api/v1/orders/{order2['order_id']}/status",
        headers=pg_merchant_headers,
        json={"status": "completed"}
    )
    assert bad_transition.status_code == 400
    assert "invalid status transition" in bad_transition.json()["detail"].lower()
