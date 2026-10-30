"""
DukaanSaathi — Test Suite for Quantity and Unit Extraction Service (Service 3)
Tests Arabic numerals, Hindi number words, colloquial fractions, unmeasurable terms,
dimension-safe conversions, and package fraction handling.
"""

from decimal import Decimal
import pytest
from backend.app.services.quantity_parser import QuantityParser
from backend.app.models import Product

def test_parse_digits_and_units():
    res1 = QuantityParser.parse_quantity_phrase("1 kg")
    assert res1.normalized_amount == Decimal("1")
    assert res1.normalized_unit == "kg"

    res2 = QuantityParser.parse_quantity_phrase("250 gram")
    assert res2.normalized_amount == Decimal("250")
    assert res2.normalized_unit == "g"

    res3 = QuantityParser.parse_quantity_phrase("2 packet")
    assert res3.normalized_amount == Decimal("2")
    assert res3.normalized_unit == "packet"

def test_parse_hindi_number_words():
    cases = [
        ("ek kilo", Decimal("1"), "kg"),
        ("do packet", Decimal("2"), "packet"),
        ("teen litre", Decimal("3"), "L"),
        ("chaar bottle", Decimal("4"), "bottle"),
        ("paanch kilo", Decimal("5"), "kg"),
        ("das jar", Decimal("10"), "jar"),
    ]
    for phrase, expected_amt, expected_unit in cases:
        res = QuantityParser.parse_quantity_phrase(phrase)
        assert res.normalized_amount == expected_amt, f"Failed amount for '{phrase}'"
        assert res.normalized_unit == expected_unit, f"Failed unit for '{phrase}'"

def test_parse_colloquial_fractions():
    cases = [
        ("aadha kilo", Decimal("0.5"), "kg"),
        ("aadha litre", Decimal("0.5"), "L"),
        ("half litre", Decimal("0.5"), "L"),
        ("pao kilo", Decimal("0.25"), "kg"),
        ("dhai sau gram", Decimal("250"), "g"),
        ("dedh kilo", Decimal("1.5"), "kg"),
        ("dhai kilo", Decimal("2.5"), "kg"),
    ]
    for phrase, expected_amt, expected_unit in cases:
        res = QuantityParser.parse_quantity_phrase(phrase)
        assert res.normalized_amount == expected_amt, f"Failed amount for '{phrase}'"
        assert res.normalized_unit == expected_unit, f"Failed unit for '{phrase}'"

def test_unmeasurable_quantity_detected():
    res1 = QuantityParser.parse_quantity_phrase("thoda sa chini")
    assert res1.is_unmeasurable is True
    assert res1.normalized_amount is None

    res2 = QuantityParser.parse_quantity_phrase("kuch biscuit")
    assert res2.is_unmeasurable is True

def test_bulk_loose_fractional_conversion(db_session):
    """Loose flour (PRD001) allows fractional weights (250g -> 0.25kg)."""
    p = db_session.query(Product).filter(Product.product_id == "PRD001").first()
    assert p is not None
    assert p.sale_unit == "kg"

    qty = QuantityParser.parse_quantity_phrase("250 gram")
    sellable_qty, sellable_unit, err = QuantityParser.resolve_package_quantity(p, qty)
    assert err is None
    assert sellable_qty == Decimal("0.25")
    assert sellable_unit == "kg"

def test_sealed_package_fraction_rejected(db_session):
    """
    CRITICAL REQUIREMENT (TC013):
    Besan (PRD003) is a sealed 1kg packet. Requesting 250g must be rejected/clarified,
    because the shopkeeper cannot split a sealed branded package.
    """
    p = db_session.query(Product).filter(Product.product_id == "PRD003").first()
    assert p is not None

    qty = QuantityParser.parse_quantity_phrase("250 gram")
    sellable_qty, sellable_unit, err = QuantityParser.resolve_package_quantity(p, qty)
    assert err == "clarify_package_fraction"
    assert sellable_qty is None

def test_milk_pouch_volume_conversion(db_session):
    """
    Amul Taaza (PRD021) is a 500ml pouch (sale_unit=packet/pouch).
    'aadha litre' (0.5L) = 1 pouch.
    '1 litre' = 2 pouches.
    '2 litre' = 4 pouches.
    """
    p = db_session.query(Product).filter(Product.product_id == "PRD021").first()
    assert p is not None

    qty_half = QuantityParser.parse_quantity_phrase("aadha litre")
    sell_half, _, err_half = QuantityParser.resolve_package_quantity(p, qty_half)
    assert err_half is None
    assert sell_half == Decimal("1")

    qty_1l = QuantityParser.parse_quantity_phrase("1 litre")
    sell_1l, _, err_1l = QuantityParser.resolve_package_quantity(p, qty_1l)
    assert err_1l is None
    assert sell_1l == Decimal("2")

    qty_2l = QuantityParser.parse_quantity_phrase("2 litre")
    sell_2l, _, err_2l = QuantityParser.resolve_package_quantity(p, qty_2l)
    assert err_2l is None
    assert sell_2l == Decimal("4")

