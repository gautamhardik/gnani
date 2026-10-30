# DukaanSaathi Starter Pack

A synthetic, single-store dataset and database starter kit for the DukaanSaathi voice-first kirana ordering prototype.

## Included

- `data/products.csv` / `.json`: 100 demo grocery products and package metadata.
- `data/product_aliases.csv` / `.json`: canonical, short and Hindi/Hinglish/English aliases. A few generic terms (such as milk/doodh) intentionally map to multiple products to test clarification.
- `data/inventory.csv`: starting stock and low-stock thresholds. Stock is tracked in each SKU's `sale_unit` (for example, kg, pouch, packet, bottle).
- `data/categories.csv`: category lookup.
- `data/store.json`: fictional demo shop profile.
- `data/voice_test_cases.csv` / `.json`: 30 utterances with gold transcripts, expected items/actions and evaluation notes.
- `data/conversation_scenarios.json`: five multi-turn conversation tests.
- `audio/recording_manifest.csv`: recording checklist for the 30 prompts. Actual recordings are not included; record them with consenting speakers.
- `database/dukkaansaathi_seed.sqlite`: ready-to-inspect SQLite database seeded with store, products, aliases and inventory.
- `database/schema_postgres.sql`: PostgreSQL schema for app deployment.
- `scripts/seed_postgres.py`: loads included CSVs into a database after schema creation.
- `docs/data_dictionary.md`: field definitions and modelling assumptions.

## Important data disclaimer

All shop, product inventory and price values are fabricated demo data for development and testing. Prices are not live market prices, and the catalogue is not affiliated with or endorsed by any listed brands. Replace them with a shop's verified prices and stock before any real commercial use. The pack contains no real customers, phone numbers, addresses or voice recordings.

## Quick start

1. Inspect `database/dukkaansaathi_seed.sqlite` with SQLite Browser or Python.
2. Use `data/products.csv`, `data/product_aliases.csv` and `data/inventory.csv` as source data for your app.
3. For PostgreSQL, create a fresh database, execute `database/schema_postgres.sql`, then set `DATABASE_URL` and run `python scripts/seed_postgres.py` (install `psycopg[binary]` first).
4. Use `data/voice_test_cases.json` to build an evaluation harness. Record each utterance to `audio/TCxxx.wav` after obtaining consent.

## Modelling notes

- `price_inr` is the price per sellable unit. For a bulk SKU with `sale_unit=kg`, this is per kg. For a packaged SKU with `sale_unit=pouch`, this is per pouch.
- `pack_size` and `pack_size_unit` describe what one sellable unit contains. Example: one 500 ml pouch.
- `inventory.stock_quantity` is measured in `inventory.stock_unit`, which should equal the product's `sale_unit`.
- The order parser should normalize user quantities to sellable units only when package conversion is exact. If not exact (for example, asking for 250 g of a fixed 1 kg bag), ask a clarification or report that the catalogue does not support that quantity.
- Generic aliases that map to multiple active SKUs must trigger clarification, not arbitrary selection.
- Do not deduct stock when an item is merely added to a draft cart. Recheck and deduct atomically only when the customer explicitly confirms the order.
- `TC015` and `TC016` are stock-boundary tests. TC015 requests exactly six jars where the demo inventory has six; TC016 requests ten where only seven are available.

## Database safety

The SQLite file is a seeded development database. Do not use this as a production database. For real use, implement authentication, authorization, rate limits, audit logs, idempotent order confirmation and transactional stock deduction.
