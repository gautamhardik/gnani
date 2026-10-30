"""
DukaanSaathi — Catalogue & Inventory Data Audit Script
Performs integrity checks on the live database to verify that all 100 products,
aliases, and inventory constraints are satisfied.
"""

import sys
from pathlib import Path
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.core.database import SessionLocal
from backend.app.models import Store, Product, ProductAlias, StoreInventory

def audit_database():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("DukaanSaathi: Authoritative Database Catalogue Audit")
        print("=" * 60)

        # 1. Store Check
        store = db.query(Store).filter(Store.store_id == "STORE001").first()
        if not store:
            raise RuntimeError("Demo store STORE001 not found in database!")
        print(f"[OK] Store Found: {store.store_name} ({store.slug})")

        # 2. Product Counts & Integrity
        products = db.query(Product).all()
        print(f"[OK] Total Products: {len(products)} (Expected: 100)")
        if len(products) != 100:
            raise RuntimeError(f"Expected 100 products, found {len(products)}")

        for p in products:
            assert p.price_inr >= 0, f"Negative price on {p.product_id}"
            assert p.pack_size > 0, f"Non-positive pack size on {p.product_id}"
            assert p.sale_unit, f"Missing sale_unit on {p.product_id}"

        # 3. Alias Counts & Integrity
        aliases = db.query(ProductAlias).all()
        print(f"[OK] Total Aliases:  {len(aliases)} (Expected: 306)")
        if len(aliases) != 306:
            raise RuntimeError(f"Expected 306 aliases, found {len(aliases)}")

        # 4. Inventory Linkage & Constraints
        inventory = db.query(StoreInventory).all()
        print(f"[OK] Inventory Rows: {len(inventory)} (Expected: 100)")
        if len(inventory) != 100:
            raise RuntimeError(f"Expected 100 inventory rows, found {len(inventory)}")

        zero_stock_count = 0
        low_stock_count = 0
        for inv in inventory:
            assert inv.stock_quantity >= 0, f"Negative stock on {inv.product_id}"
            assert inv.reserved_quantity >= 0, f"Negative reserved on {inv.product_id}"
            if inv.stock_quantity == 0:
                zero_stock_count += 1
            if inv.stock_quantity <= inv.low_stock_threshold:
                low_stock_count += 1

        print(f"[OK] Low stock items: {low_stock_count}, Out of stock items: {zero_stock_count}")
        print("=" * 60)
        print("[SUCCESS] All database catalogue audit constraints passed!")
        print("=" * 60)
        return True
    finally:
        db.close()

if __name__ == "__main__":
    success = audit_database()
    sys.exit(0 if success else 1)
