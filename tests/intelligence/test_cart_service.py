"""
DukaanSaathi — Test Suite for Cart Service (Service 5)
Tests cart mutations, subtotal calculation, quantity replacement, item removal, and total summation.
"""

from decimal import Decimal
from backend.app.services.cart_service import CartService

def test_add_and_increment_item():
    cart = CartService()
    item1 = cart.add_or_update_item(
        product_id="PRD001",
        name="Loose Wheat Flour (Atta)",
        quantity=Decimal("1"),
        unit="kg",
        unit_price=Decimal("38.00")
    )
    assert item1.quantity == Decimal("1")
    assert item1.subtotal == Decimal("38.00")
    assert cart.calculate_total() == Decimal("38.00")

    # Increment same item
    item2 = cart.add_or_update_item(
        product_id="PRD001",
        name="Loose Wheat Flour (Atta)",
        quantity=Decimal("2"),
        unit="kg",
        unit_price=Decimal("38.00")
    )
    assert item2.quantity == Decimal("3")
    assert item2.subtotal == Decimal("114.00")
    assert cart.calculate_total() == Decimal("114.00")

def test_replace_quantity():
    cart = CartService()
    cart.add_or_update_item(
        product_id="PRD034",
        name="Sugar (Loose)",
        quantity=Decimal("1"),
        unit="kg",
        unit_price=Decimal("44.00")
    )
    assert cart.calculate_total() == Decimal("44.00")

    # Replace with 0.5 kg ("Nahi, aadha kilo kar do")
    updated = cart.set_item_quantity("PRD034", Decimal("0.5"))
    assert updated is not None
    assert updated.quantity == Decimal("0.5")
    assert updated.subtotal == Decimal("22.00")
    assert cart.calculate_total() == Decimal("22.00")

def test_remove_item():
    cart = CartService()
    cart.add_or_update_item("PRD041", "Maggi 2-Minute Noodles 70g", Decimal("2"), "packet", Decimal("14.00"))
    cart.add_or_update_item("PRD042", "Parle-G Gold Biscuits 100g", Decimal("1"), "packet", Decimal("10.00"))
    assert len(cart.get_items()) == 2
    assert cart.calculate_total() == Decimal("38.00")

    removed = cart.remove_item("PRD041")
    assert removed is True
    assert len(cart.get_items()) == 1
    assert cart.get_items()[0].product_id == "PRD042"
    assert cart.calculate_total() == Decimal("10.00")

def test_clear_cart():
    cart = CartService()
    cart.add_or_update_item("PRD001", "Loose Atta", Decimal("1"), "kg", Decimal("38.00"))
    cart.clear()
    assert len(cart.get_items()) == 0
    assert cart.calculate_total() == Decimal("0.00")

