"""
DukaanSaathi — Test Suite for Inventory Integration Service (Service 7)
Tests stock availability checks, boundary conditions, insufficient stock detection,
and verifies zero database stock mutations occur.
"""

from decimal import Decimal
import pytest
from backend.app.services.inventory_service import InventoryService
from backend.app.models import StoreInventory, StockMovement

def test_stock_availability_and_boundary(db_session):
    inv_service = InventoryService(db_session)

    # Set up exact test stock for boundary verification
    inv = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD001").first()
    assert inv is not None
    original_stock = inv.stock_quantity

    # 1. Normal available quantity
    is_avail, stock, _ = inv_service.check_availability("PRD001", Decimal("2"))
    assert is_avail is True
    assert stock == original_stock

    # 2. Exact boundary test (TC015: requested == current_stock)
    is_boundary, _, _ = inv_service.check_availability("PRD001", original_stock)
    assert is_boundary is True

    # 3. Insufficient stock test (TC016: requested > current_stock)
    is_insufficient, _, _ = inv_service.check_availability("PRD001", original_stock + Decimal("1"))
    assert is_insufficient is False

def test_authoritative_price_retrieval(db_session):
    inv_service = InventoryService(db_session)
    price_atta = inv_service.get_authoritative_price("PRD001")
    assert price_atta == Decimal("42.00")

    price_maggi = inv_service.get_authoritative_price("PRD041")
    assert price_maggi == Decimal("14.00")

    price_none = inv_service.get_authoritative_price("NONEXISTENT")
    assert price_none is None

def test_critical_invariant_zero_stock_deduction(db_session):
    """
    CRITICAL BUSINESS INVARIANT:
    Checking inventory or building conversational orders must NEVER deduct stock
    or write to the stock_movements table. Stock is only deducted on shopkeeper acceptance.
    """
    inv_service = InventoryService(db_session)

    inv_before = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD001").first()
    stock_before = inv_before.stock_quantity
    movements_before_count = db_session.query(StockMovement).count()

    # Perform multiple availability checks
    inv_service.check_availability("PRD001", Decimal("5"))
    inv_service.check_availability("PRD001", Decimal("500"))

    db_session.expire_all()
    inv_after = db_session.query(StoreInventory).filter(StoreInventory.product_id == "PRD001").first()
    movements_after_count = db_session.query(StockMovement).count()

    assert inv_after.stock_quantity == stock_before, "Stock was mutated during availability check!"
    assert movements_after_count == movements_before_count, "Stock movement was logged during availability check!"
