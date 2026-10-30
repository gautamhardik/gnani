"""
DukaanSaathi — Validated Database Seed Script (Phase 2)
Loads and validates the 100-product starter pack catalogue, aliases, and inventory.
Idempotent and database-agnostic (works on PostgreSQL and SQLite).
"""

import os
import sys
import csv
import json
from decimal import Decimal
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import text

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.core.config import settings
from backend.app.core.database import engine, SessionLocal
from backend.app.models import (
    Base,
    Store,
    Product,
    ProductAlias,
    StoreInventory,
)

DATA_DIR = ROOT / "data" / "data"

def load_csv(filename: str):
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing starter pack file: {path}")
    with open(path, mode="r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def load_json(filename: str):
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing starter pack file: {path}")
    with open(path, mode="r", encoding="utf-8") as f:
        return json.load(f)

def validate_starter_pack(store_data: dict, products_data: list, aliases_data: list, inventory_data: list):
    """Rigorous pre-flight validation of catalogue rows before database write."""
    print("[VALIDATION] Checking starter pack integrity...")
    errors = []

    # 1. Validate Store
    if not store_data.get("store_id") or not store_data.get("store_name"):
        errors.append("Invalid store profile in store.json")

    # 2. Validate Products
    if len(products_data) != 100:
        errors.append(f"Expected 100 products, found {len(products_data)}")

    product_ids = set()
    for idx, p in enumerate(products_data, start=1):
        pid = p.get("product_id")
        if not pid:
            errors.append(f"Product row {idx} missing product_id")
            continue
        product_ids.add(pid)
        try:
            price = Decimal(p["price_inr"])
            if price < 0:
                errors.append(f"Product {pid} has negative price: {price}")
        except Exception:
            errors.append(f"Product {pid} invalid price: {p.get('price_inr')}")

        try:
            pack_size = Decimal(p["pack_size"])
            if pack_size <= 0:
                errors.append(f"Product {pid} non-positive pack size: {pack_size}")
        except Exception:
            errors.append(f"Product {pid} invalid pack size: {p.get('pack_size')}")

    # 3. Validate Aliases
    if len(aliases_data) != 306:
        errors.append(f"Expected 306 aliases, found {len(aliases_data)}")

    alias_ids = set()
    for idx, a in enumerate(aliases_data, start=1):
        aid = a.get("alias_id")
        pid = a.get("product_id")
        if not aid or aid in alias_ids:
            errors.append(f"Duplicate or missing alias_id {aid} at row {idx}")
        alias_ids.add(aid)
        if pid not in product_ids:
            errors.append(f"Alias {aid} references non-existent product_id: {pid}")
        if not a.get("normalized_alias"):
            errors.append(f"Alias {aid} missing normalized_alias")

    # 4. Validate Inventory
    if len(inventory_data) != 100:
        errors.append(f"Expected 100 inventory rows, found {len(inventory_data)}")

    inv_product_ids = set()
    for idx, inv in enumerate(inventory_data, start=1):
        pid = inv.get("product_id")
        if not pid or pid in inv_product_ids:
            errors.append(f"Duplicate or missing inventory product_id {pid} at row {idx}")
        inv_product_ids.add(pid)
        if pid not in product_ids:
            errors.append(f"Inventory references non-existent product_id: {pid}")
        try:
            stock = Decimal(inv["stock_quantity"])
            if stock < 0:
                errors.append(f"Inventory {pid} has negative stock: {stock}")
        except Exception:
            errors.append(f"Inventory {pid} invalid stock quantity: {inv.get('stock_quantity')}")

    if errors:
        print(f"[FATAL] Starter pack validation failed with {len(errors)} errors:")
        for err in errors[:10]:
            print(f"  - {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
        raise ValueError("Starter pack catalogue validation failed")

    print(f"[VALIDATION PASSED] 1 store, {len(product_ids)} products, {len(alias_ids)} aliases, {len(inv_product_ids)} inventory records verified.")


def seed_database(db: Session, bind_engine=None):
    """Performs schema initialization and loads validated starter pack."""
    target_engine = bind_engine or engine
    print(f"[SEED] Initializing schema on target database...")
    Base.metadata.create_all(bind=target_engine)

    store_data = load_json("store.json")
    products_data = load_csv("products.csv")
    aliases_data = load_csv("product_aliases.csv")
    inventory_data = load_csv("inventory.csv")

    validate_starter_pack(store_data, products_data, aliases_data, inventory_data)

    print("[SEED] Commencing database upsert transaction...")

    # 1. Upsert Store
    store = db.query(Store).filter(Store.store_id == store_data["store_id"]).first()
    if not store:
        store = Store(
            store_id=store_data["store_id"],
            store_name=store_data["store_name"],
            slug=store_data["slug"],
            currency=store_data.get("currency", "INR"),
            timezone=store_data.get("timezone", "Asia/Kolkata")
        )
        db.add(store)
    else:
        store.store_name = store_data["store_name"]
        store.slug = store_data["slug"]
    db.flush()

    # 2. Upsert Products
    for p in products_data:
        prod = db.query(Product).filter(Product.product_id == p["product_id"]).first()
        is_active = p["is_active"].strip().lower() == "true"
        if not prod:
            prod = Product(
                product_id=p["product_id"],
                store_id=store.store_id,
                sku=p["sku"],
                name=p["name"],
                brand=p.get("brand") or None,
                category=p["category"],
                sale_unit=p["sale_unit"],
                pack_size=Decimal(p["pack_size"]),
                pack_size_unit=p["pack_size_unit"],
                price_inr=Decimal(p["price_inr"]),
                is_active=is_active,
                description=p.get("description") or None
            )
            db.add(prod)
        else:
            prod.name = p["name"]
            prod.brand = p.get("brand") or None
            prod.category = p["category"]
            prod.sale_unit = p["sale_unit"]
            prod.pack_size = Decimal(p["pack_size"])
            prod.pack_size_unit = p["pack_size_unit"]
            prod.price_inr = Decimal(p["price_inr"])
            prod.is_active = is_active
            prod.description = p.get("description") or None
    db.flush()

    # 3. Upsert Product Aliases
    for a in aliases_data:
        alias_obj = db.query(ProductAlias).filter(ProductAlias.alias_id == a["alias_id"]).first()
        if not alias_obj:
            alias_obj = ProductAlias(
                alias_id=a["alias_id"],
                product_id=a["product_id"],
                alias=a["alias"],
                normalized_alias=a["normalized_alias"],
                language=a.get("language", "hi-Latn"),
                alias_type=a.get("alias_type", "colloquial")
            )
            db.add(alias_obj)
        else:
            alias_obj.alias = a["alias"]
            alias_obj.normalized_alias = a["normalized_alias"]
            alias_obj.language = a.get("language", "hi-Latn")
            alias_obj.alias_type = a.get("alias_type", "colloquial")
    db.flush()

    # 4. Upsert Inventory
    for inv in inventory_data:
        inv_obj = db.query(StoreInventory).filter(StoreInventory.product_id == inv["product_id"]).first()
        if not inv_obj:
            inv_obj = StoreInventory(
                product_id=inv["product_id"],
                stock_quantity=Decimal(inv["stock_quantity"]),
                stock_unit=inv["stock_unit"],
                low_stock_threshold=Decimal(inv.get("low_stock_threshold", 0)),
                reserved_quantity=Decimal(inv.get("reserved_quantity", 0))
            )
            db.add(inv_obj)
        else:
            inv_obj.stock_quantity = Decimal(inv["stock_quantity"])
            inv_obj.stock_unit = inv["stock_unit"]
            inv_obj.low_stock_threshold = Decimal(inv.get("low_stock_threshold", 0))
            inv_obj.reserved_quantity = Decimal(inv.get("reserved_quantity", 0))
    db.flush()

    db.commit()

    # Verification counts
    store_cnt = db.query(Store).count()
    prod_cnt = db.query(Product).count()
    alias_cnt = db.query(ProductAlias).count()
    inv_cnt = db.query(StoreInventory).count()

    print("[SUCCESS] Seed completed and verified:")
    print(f"          Stores:    {store_cnt}")
    print(f"          Products:  {prod_cnt}")
    print(f"          Aliases:   {alias_cnt}")
    print(f"          Inventory: {inv_cnt}")

    assert store_cnt >= 1, "Verification failed: Store count < 1"
    assert prod_cnt == 100, f"Verification failed: Product count {prod_cnt} != 100"
    assert alias_cnt == 306, f"Verification failed: Alias count {alias_cnt} != 306"
    assert inv_cnt == 100, f"Verification failed: Inventory count {inv_cnt} != 100"

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
