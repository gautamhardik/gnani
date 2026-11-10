import pytest
from backend.app.models import Store, Product, ProductAlias, StoreInventory

def test_starter_pack_database_integrity(db_session):
    """
    Verifies that all 100 products, 306 aliases, 100 inventory rows,
    and the demo store from the starter pack are present and valid.
    """
    # 1. Store
    store = db_session.query(Store).filter(Store.store_id == "STORE001").first()
    assert store is not None
    assert store.store_name == "Everyday Needs General Store"
    assert store.slug == "everyday-needs-general-store"

    # 2. Products count
    prod_count = db_session.query(Product).count()
    assert prod_count >= 100

    # 3. Aliases count
    alias_count = db_session.query(ProductAlias).count()
    assert alias_count >= 306

    # 4. Inventory count
    inv_count = db_session.query(StoreInventory).count()
    assert inv_count >= 100

    # 5. Check specific known items from starter pack
    aata = db_session.query(Product).filter(Product.product_id == "PRD001").first()
    assert aata is not None
    assert "Atta" in aata.name or "Wheat Flour" in aata.name
    assert aata.sale_unit == "kg"
    assert aata.price_inr > 0

    aashirvaad = db_session.query(Product).filter(Product.product_id == "PRD002").first()
    assert aashirvaad is not None
    assert "Aashirvaad" in aashirvaad.name

    maggi = db_session.query(Product).filter(Product.product_id == "PRD041").first()
    assert maggi is not None
    assert "Maggi" in maggi.name
    assert maggi.sale_unit == "packet"
