"""
DukaanSaathi — Phase 7 PostgreSQL Concurrency & Row-Level Locking Verification
TASK 6: Rigorous verification of PostgreSQL row-level locks (with_for_update)
under concurrent conflicting order acceptance transactions.
NEVER uses SQLite as evidence; runs strictly against PostgreSQL 16.6.
"""

from decimal import Decimal
import concurrent.futures
import time
import pytest
from sqlalchemy.orm import Session
from backend.app.models import StoreInventory, Order, StockMovement

def test_concurrent_acceptance_conflicting_orders_single_stock_item(pg_client, pg_db, pg_session_factory, pg_merchant_headers):
    """
    TASK 6 Primary Concurrency Test:
    Two separate orders compete for the last 1 remaining unit in stock.
    Using two distinct PostgreSQL transactions:
    - Exactly ONE must succeed (HTTP 200).
    - Exactly ONE must fail with conflict (HTTP 409).
    - Final stock in PostgreSQL must be exactly 0.
    - Exactly ONE deduction audit row must exist in stock_movements.
    """
    product_id = "PRD010"  # Dedicated item for concurrency test
    store_id = "STORE001"

    # Step 1: Set stock to exactly 1.0 in PostgreSQL
    inv = pg_db.query(StoreInventory).filter(StoreInventory.product_id == product_id).first()
    assert inv is not None
    inv.stock_quantity = Decimal("1.0")
    pg_db.commit()

    # Step 2: Create two distinct pending orders, each requesting 1.0 unit
    resp_a = pg_client.post("/api/v1/orders", json={
        "store_id": store_id,
        "items": [{"product_id": product_id, "quantity": 1.0}]
    })
    assert resp_a.status_code in (200, 201)
    order_a_id = resp_a.json()["order_id"]

    resp_b = pg_client.post("/api/v1/orders", json={
        "store_id": store_id,
        "items": [{"product_id": product_id, "quantity": 1.0}]
    })
    assert resp_b.status_code in (200, 201)
    order_b_id = resp_b.json()["order_id"]

    # Verify both are pending and stock is still 1.0
    pg_db.expire_all()
    inv_check = pg_db.query(StoreInventory).filter(StoreInventory.product_id == product_id).first()
    assert Decimal(str(inv_check.stock_quantity)) == Decimal("1.0")

    # Step 3: Issue concurrent acceptance requests via ThreadPoolExecutor
    def accept_order_task(order_id: str):
        # Fresh client call ensuring separate request lifecycle and db connection checkout
        return pg_client.post(
            f"/api/v1/orders/{order_id}/accept",
            headers=pg_merchant_headers
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(accept_order_task, order_a_id)
        future_b = executor.submit(accept_order_task, order_b_id)
        res_a = future_a.result()
        res_b = future_b.result()

    # Step 4: Verify HTTP responses
    statuses = sorted([res_a.status_code, res_b.status_code])
    assert statuses == [200, 409], (
        f"Expected exactly one 200 OK and one 409 Conflict, got {statuses}. "
        f"Order A ({order_a_id}): {res_a.status_code} - {res_a.text}; "
        f"Order B ({order_b_id}): {res_b.status_code} - {res_b.text}"
    )

    # Identify winner and loser
    winner_res = res_a if res_a.status_code == 200 else res_b
    loser_res = res_b if res_a.status_code == 200 else res_a
    assert "insufficient stock" in loser_res.json()["detail"].lower()

    # Step 5: Verify authoritative state in PostgreSQL database
    pg_db.expire_all()

    # Final stock MUST be exactly 0.0 (NOT -1.0 or double deducted)
    final_inv = pg_db.query(StoreInventory).filter(StoreInventory.product_id == product_id).first()
    assert Decimal(str(final_inv.stock_quantity)) == Decimal("0.0"), (
        f"Expected final stock to be 0.0, but got {final_inv.stock_quantity}"
    )

    # Exactly ONE deduction audit row must exist for this race
    movements = pg_db.query(StockMovement).filter(
        StockMovement.product_id == product_id,
        StockMovement.reason == "merchant_order_accepted",
        StockMovement.order_id.in_([order_a_id, order_b_id])
    ).all()
    assert len(movements) == 1, f"Expected exactly 1 audit movement, found {len(movements)}"
    assert Decimal(str(movements[0].change_quantity)) == Decimal("-1.0")

    # Winner is 'accepted', Loser remains 'pending'
    winning_order_id = winner_res.json()["order_id"]
    losing_order_id = order_a_id if winning_order_id == order_b_id else order_b_id

    winning_order = pg_db.query(Order).filter(Order.order_id == winning_order_id).first()
    losing_order = pg_db.query(Order).filter(Order.order_id == losing_order_id).first()
    assert winning_order.status == "accepted"
    assert losing_order.status == "pending"


def test_concurrent_duplicate_acceptance_same_order(pg_client, pg_db, pg_merchant_headers):
    """
    TASK 6 Secondary Concurrency Test:
    Two simultaneous requests try to accept the EXACT SAME order.
    Using PostgreSQL row-level lock on the Order record:
    - Exactly ONE succeeds (HTTP 200).
    - The second receives HTTP 409 (not in pending status).
    - Stock is deducted exactly ONCE (no double deduction).
    - Exactly ONE audit movement row is created.
    """
    product_id = "PRD011"
    store_id = "STORE001"

    # Set stock to 10.0
    inv = pg_db.query(StoreInventory).filter(StoreInventory.product_id == product_id).first()
    assert inv is not None
    inv.stock_quantity = Decimal("10.0")
    pg_db.commit()

    # Place order for 2.0 units
    resp = pg_client.post("/api/v1/orders", json={
        "store_id": store_id,
        "items": [{"product_id": product_id, "quantity": 2.0}]
    })
    assert resp.status_code in (200, 201)
    order_id = resp.json()["order_id"]

    # Issue duplicate acceptance requests concurrently
    def accept_same_order():
        return pg_client.post(
            f"/api/v1/orders/{order_id}/accept",
            headers=pg_merchant_headers
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(accept_same_order)
        f2 = executor.submit(accept_same_order)
        r1 = f1.result()
        r2 = f2.result()

    statuses = sorted([r1.status_code, r2.status_code])
    assert statuses == [200, 409], f"Expected [200, 409], got {statuses}"

    # Verify stock deducted exactly ONCE (10.0 - 2.0 = 8.0, NOT 6.0)
    pg_db.expire_all()
    final_inv = pg_db.query(StoreInventory).filter(StoreInventory.product_id == product_id).first()
    assert Decimal(str(final_inv.stock_quantity)) == Decimal("8.0")

    # Verify exactly 1 stock movement row created
    movements = pg_db.query(StockMovement).filter(
        StockMovement.order_id == order_id,
        StockMovement.reason == "merchant_order_accepted"
    ).all()
    assert len(movements) == 1
    assert Decimal(str(movements[0].change_quantity)) == Decimal("-2.0")
