"""Seed a fresh PostgreSQL database from the included CSV files.
Usage: set DATABASE_URL, then python scripts/seed_postgres.py
First run database/schema_postgres.sql against that database.
"""
import csv, os
from pathlib import Path
import psycopg
ROOT=Path(__file__).resolve().parents[1]
url=os.environ.get("DATABASE_URL")
if not url: raise SystemExit("Set DATABASE_URL first")
def rows(name):
    with open(ROOT/"data"/name, newline="", encoding="utf-8-sig") as f: return list(csv.DictReader(f))
with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        s=__import__("json").loads((ROOT/"data/store.json").read_text(encoding="utf-8"))
        cur.execute("INSERT INTO stores(store_id,store_name,slug,currency,timezone) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(store_id) DO NOTHING",(s["store_id"],s["store_name"],s["slug"],s["currency"],s["timezone"]))
        for p in rows("products.csv"):
            cur.execute("INSERT INTO products(product_id,store_id,sku,name,brand,category,sale_unit,pack_size,pack_size_unit,price_inr,is_active,description) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(product_id) DO NOTHING",(p["product_id"],s["store_id"],p["sku"],p["name"],p["brand"],p["category"],p["sale_unit"],p["pack_size"],p["pack_size_unit"],p["price_inr"],p["is_active"].lower()=="true",p["description"]))
        for a in rows("product_aliases.csv"):
            cur.execute("INSERT INTO product_aliases(alias_id,product_id,alias,normalized_alias,language,alias_type) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(alias_id) DO NOTHING",tuple(a[k] for k in ["alias_id","product_id","alias","normalized_alias","language","alias_type"]))
        for x in rows("inventory.csv"):
            cur.execute("INSERT INTO inventory(product_id,stock_quantity,stock_unit,low_stock_threshold,reserved_quantity) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(product_id) DO NOTHING",(x["product_id"],x["stock_quantity"],x["stock_unit"],x["low_stock_threshold"],x["reserved_quantity"]))
print("Seed complete: 100 demo products, aliases and inventory loaded.")
