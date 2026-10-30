import pytest
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from backend.app.models import (
    Store,
    Product,
    ProductAlias,
    StoreInventory,
    Customer,
    OrderSession,
    Order,
    OrderItem,
    StockMovement,
)

def test_store_creation_and_unique_slug(db_session):
    store = Store(
        store_id="TEST_STORE_99",
        store_name="Unique Test Kirana",
        slug="unique-test-kirana",
        currency="INR",
        timezone="Asia/Kolkata"
    )
    db_session.add(store)
    db_session.commit()

    # Attempt duplicate slug
    dup_store = Store(
        store_id="TEST_STORE_100",
        store_name="Another Store",
        slug="unique-test-kirana"
    )
    db_session.add(dup_store)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_product_and_inventory_constraints(db_session):
    # Valid product
    p = Product(
        product_id="TEST_PRD_001",
        store_id="STORE001",
        sku="TEST-SKU-001",
        name="Test Item 1",
        category="Test Category",
        sale_unit="packet",
        pack_size=Decimal("1.000"),
        pack_size_unit="packet",
        price_inr=Decimal("50.00"),
        is_active=True
    )
    db_session.add(p)
    db_session.commit()

    inv = StoreInventory(
        product_id="TEST_PRD_001",
        stock_quantity=Decimal("10.000"),
        stock_unit="packet",
        low_stock_threshold=Decimal("2.000"),
        reserved_quantity=Decimal("0.000")
    )
    db_session.add(inv)
    db_session.commit()

    assert inv.product.name == "Test Item 1"

def test_alias_foreign_key_and_cascade(db_session):
    p = Product(
        product_id="TEST_CASCADE_PRD",
        store_id="STORE001",
        sku="CASCADE-SKU",
        name="Cascade Item",
        category="Test",
        sale_unit="kg",
        pack_size=Decimal(1),
        pack_size_unit="kg",
        price_inr=Decimal(25),
        is_active=True
    )
    db_session.add(p)
    db_session.commit()

    alias = ProductAlias(
        alias_id="TEST_ALS_01",
        product_id="TEST_CASCADE_PRD",
        alias="Cascade Namak",
        normalized_alias="cascade namak",
        language="hi-Latn",
        alias_type="colloquial"
    )
    db_session.add(alias)
    db_session.commit()

    # Delete product and verify alias cascades
    db_session.delete(p)
    db_session.commit()

    remaining_alias = db_session.query(ProductAlias).filter(ProductAlias.alias_id == "TEST_ALS_01").first()
    assert remaining_alias is None
