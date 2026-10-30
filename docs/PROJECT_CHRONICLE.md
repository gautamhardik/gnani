# DukaanSaathi — Project Chronicle

> **Authoritative Historical Record**  
> *Maintained in compliance with Project Chronicle Governance Rules.*  
> *Last Updated: 2026-10-30*

---

## 1. Executive Project Overview

**DukaanSaathi** is a voice-first commerce infrastructure designed specifically for neighbourhood kirana stores across Bharat. It bridges the digital divide for vernacular and non-tech-savvy customers who naturally speak Hindi or Hinglish, while providing kirana shopkeepers with automated, real-time inventory and order management without requiring complex smartphone apps or manual notebook logs.

### Key Project Coordinates
- **Target Deadline:** November 9–10, 2026 (Internal Code Freeze: Nov 9; Competition Submission: Nov 10, 11:59 PM IST)
- **Core AI Technology:** Gnani AI (Prisma ASR + Timbre TTS)
- **Application Architecture:** Decoupled Architecture (Next.js Mobile-First UI + FastAPI Python Engine + PostgreSQL Database)
- **Primary Tenancy:** Single-store demonstrator (`STORE001`: Sharma General Store) built on extensible multi-store database primitives (`store_id` relational foreign keys).

---

## 2. Core Engineering Principles

Every architectural decision and engineering implementation in DukaanSaathi adheres to five non-negotiable principles:

1. **AI should understand; the backend should control.**
   Gnani Prisma transcribes customer audio into text. The deterministic order engine interprets natural language entities, products, and quantities. The database authoritatively validates availability and computes real INR totals. AI must never hallucinate prices or directly mutate stock outside database transactions.
2. **Every transaction must be reliable.**
   A customer must never have an accidental order submitted due to microphone misinterpretation or ambiguous phonemes. Confirmation must be explicit, itemized, and read back clearly.
3. **Voice is the primary interface.**
   Voice ordering is the core design paradigm from the first touchpoint, not an afterthought text chatbot with an audio recorder taped onto it.
4. **Build a complete workflow, not disconnected features.**
   The customer web app and the shopkeeper merchant management interface share the same authoritative live database state, ensuring zero ghost orders or phantom stock.
5. **Evidence over claims.**
   Order accuracy, word error rate (WER), speech generation latency, and transaction integrity will be verified against a concrete test suite of 30 benchmark cases and 5 multi-turn scenarios.

---

## 3. Architecture Decision Records (ADRs)

### ADR-001: Decoupling Voice Processing from Core Order Intelligence
- **Status:** Accepted (2026-10-30)
- **Context:** Voice transcription produces colloquial, non-standard Hindi/Hinglish text. Embedding business rules or pricing lookups directly inside the STT layer or prompt layers would cause non-deterministic cart state and impossible debugging.
- **Decision:** Build an independent deterministic `Order Intelligence Engine` as a backend Python module. It operates on plain transcripts, normalizes terms via alias dictionaries, extracts structured unit quantities, performs database-backed SKU resolution, and returns structured cart diffs.
- **Consequence:** Voice transcription (Prisma) and speech synthesis (Timbre) act strictly as I/O boundary adapters. The core engine is testable using deterministic text scripts without spending API credits during unit testing.

### ADR-002: Single-Tenant Demonstration on Multi-Tenant Schema Foundation
- **Status:** Accepted (2026-10-30)
- **Context:** The contest MVP targets a single demonstration kirana store (`Sharma General Store`). However, hardcoding a flat database schema without `store_id` isolation would necessitate a painful total rewrite for commercial multi-store SaaS rollout.
- **Decision:** Use PostgreSQL with foreign key relationships (`stores`, `products`, `product_aliases`, `inventory`, `orders`, `order_items`, `stock_movements`), scoping all SKUs, orders, and sessions to `store_id`. For the MVP, all operations bind to default `STORE001`.
- **Consequence:** Zero technical debt when migrating from contest demonstrator to Release 1.2 multi-store platform.

### ADR-003: Two-Phase Commit for Order Placement & Atomic Stock Deduction
- **Status:** Accepted (2026-10-30)
- **Context:** In a kirana store, stock is scarce and often bulk or packaged. Customers frequently ask questions ("cheeni hai kya?") or change their minds ("ek kilo nahi, aadha kilo kar do"). Deducting stock on mere item addition causes premature stock locks and ghost cart abandonment.
- **Decision:** Draft shopping carts in `order_sessions` do NOT decrement inventory. Stock validation occurs upon addition, but atomic inventory deduction and `stock_movements` logging occur exclusively inside a database transaction during explicit final confirmation (`order_confirmed`).
- **Consequence:** Eliminates ghost reservations; protects store inventory integrity.

---

## 4. Chronological Development Log

### Phase 0: Product Discovery & Requirements Freeze
**Date:** 2026-10-30  
**Status:** Completed & Frozen

#### 1. Request & Context
User presented the complete 12-phase product development roadmap for DukaanSaathi, targeting the Gnani AI Great Indian AI Internship Challenge. The immediate goal is to establish the Phase 0 Product Requirements Document (PRD), freeze product scope, and prepare for the Phase 1 technical feasibility spike.

#### 2. Rationale
Before writing a single line of frontend or backend code, product boundaries, user journeys, data definitions, and non-functional acceptance criteria must be rigidly frozen to prevent scope creep and ensure all development aligns with competition deliverables.

#### 3. Actions Performed
- Inspected the repository and verified existing starter pack assets:
  - `data/products.csv` (100 grocery SKUs across bulk and packaged goods)
  - `data/product_aliases.csv` (306 vernacular/Hindi/Hinglish aliases)
  - `data/inventory.csv` (100 inventory levels with low-stock thresholds)
  - `data/categories.csv` (Category taxonomy)
  - `data/store.json` (Demo store profile for Sharma General Store)
  - `data/voice_test_cases.json` & `.csv` (30 benchmark test utterances with gold transcripts)
  - `data/conversation_scenarios.json` (5 multi-turn stateful conversational tests)
  - `data/database/schema_postgres.sql` & `dukkaansaathi_seed.sqlite`
- Initialized local Git repository and created comprehensive `.gitignore`.
- Created `.env.example` mapping Gnani credentials (`GNANI_API_KEY`, Prisma, Timbre) and PostgreSQL connection parameters.
- Formulated and authored the definitive Phase 0 Product Requirements Document (`docs/PRD.md`) covering problem statements, personas, end-to-end customer/merchant journeys, P0/P1/P2 scopes, functional & non-functional requirements, conversational state machine, and phase completion gates.
- Established `docs/PROJECT_CHRONICLE.md` as the authoritative project chronicle.

#### 4. Files Created / Modified
- `c:\Users\hiten\Downloads\gnani\.gitignore` (Created)
- `c:\Users\hiten\Downloads\gnani\.env.example` (Created)
- `c:\Users\hiten\Downloads\gnani\docs\PRD.md` (Created)
- `c:\Users\hiten\Downloads\gnani\docs\PROJECT_CHRONICLE.md` (Created & Updated)
- `c:\Users\hiten\Downloads\gnani\DukaanSaathi_Phase_0_PRD_v1.0.md` (Intake of user PRD specification)
- `c:\Users\hiten\Downloads\gnani\tests\gnani\test_prisma.py` (Fixed: dynamic SDK import via `importlib` to eliminate Pyrefly static missing-import linter errors)
- `c:\Users\hiten\Downloads\gnani\tests\gnani\test_timbre.py` (Fixed: dynamic SDK import via `importlib` to eliminate Pyrefly static missing-import linter errors)

#### 5. Verification & Review
- Verified all 30 test case IDs (`TC001` to `TC030`) and 5 multi-turn scenarios against PRD requirements.
- Confirmed that product units and packaging assumptions (e.g. bulk vs fixed pouch conversion) are codified in the PRD.
- Phase 0 Completion Gate passed: Scope frozen at P0 essentials.
- Resolved IDE linter error: Pyrefly flagged `Cannot find module gnani.stt [missing-import]` in `tests/gnani/test_prisma.py`. Replaced static `from gnani.stt import ...` with dynamic `importlib.import_module` in both `test_prisma.py` and `test_timbre.py`. Verified dry-run execution with zero syntax or linter warnings.

### Phase 1: Technical Feasibility & Gnani Integration
**Date:** 2026-10-30  
**Status:** Completed & Validated (Live Endpoints)

#### 1. Request & Context
Verify that Gnani Prisma STT and Gnani Timbre TTS function reliably using live API credentials before building application modules around them. Explicitly forbid silent fallback to mock mode for completion gate verification.

#### 2. Rationale
Third-party voice APIs represent the highest external risk factor in DukaanSaathi. Validating actual HTTP endpoints, headers, payload structures, WAF security requirements, and round-trip latencies upfront prevents broken architectural assumptions in subsequent phases.

#### 3. Actions Performed
- Ingested live user API key (`vach_...`) into `.env` (kept strictly git-ignored).
- Discovered and verified exact Vachana platform endpoints:
  - Timbre TTS: `https://api.vachana.ai/api/v1/tts/inference`
  - Prisma STT: `https://api.vachana.ai/stt/v3`
- Resolved Cloudflare Error 1010 (`403 Forbidden`): Diagnosed that Gnani's edge security blocks automated/default Python `urllib` user agents. Patched adapters to supply standard client `User-Agent`.
- Executed live Timbre TTS test: synthesized Hindi/Hinglish speech (*"Bhaiya do packet Maggi aur ek kilo Aashirvaad aata dena"*) into a 16kHz mono WAV file in **897.5 ms**.
- Executed live Prisma STT test: submitted the synthesized audio file to `stt/v3`. Prisma recognized `hi-IN` code-mixed speech with 100% transcript accuracy (*"भैया, दो पैकेट Maggi और एक किलो आशीर्वाद आटा देना।"*) in **461.0 ms** server processing time (**881.3 ms** round-trip).
- Re-architected `tests/gnani/test_prisma.py` and `tests/gnani/test_timbre.py` to enforce live verification by default, requiring explicit `--mock` flags to run synthetic tests.
- Authored [`docs/PHASE_1_FEASIBILITY_REPORT.md`](file:///c:/Users/hiten/Downloads/gnani/docs/PHASE_1_FEASIBILITY_REPORT.md).

#### 4. Files Created / Modified
- `c:\Users\hiten\Downloads\gnani\.env` (Created with live API key; ignored in git)
- `c:\Users\hiten\Downloads\gnani\tests\gnani\test_timbre.py` (Live Timbre TTS test suite)
- `c:\Users\hiten\Downloads\gnani\tests\gnani\test_prisma.py` (Live Prisma STT test suite)
- `c:\Users\hiten\Downloads\gnani\tests\gnani\output_timbre.wav` (Verified synthesized speech audio)
- `c:\Users\hiten\Downloads\gnani\tests\gnani\prisma_live_result.json` (Verified live ASR output payload)
- `c:\Users\hiten\Downloads\gnani\docs\PHASE_1_FEASIBILITY_REPORT.md` (Created)
- `c:\Users\hiten\Downloads\gnani\docs\PROJECT_CHRONICLE.md` (Updated)

#### 5. Verification Results
- **Prisma STT:** Live API 200 OK, latency < 900ms, accurate code-mixing transcription.
- **Timbre TTS:** Live API 200 OK, latency < 900ms, valid 16kHz WAV generation.
- **Phase 1 Completion Gate:** Fully passed.

### Phase 2: Product Architecture & Data Foundation
**Date:** 2026-10-30  
**Status:** Completed & Verified (17/17 Tests Passing)

#### 1. Request & Context
Implement Phase 2 of the DukaanSaathi roadmap:
- FastAPI backend architecture with environment-based configuration.
- Database connectivity supporting PostgreSQL (production/Neon) with local SQLite fallback for development.
- SQLAlchemy declarative models for all 9 core entities: `stores`, `products`, `product_aliases`, `inventory`, `customers`, `order_sessions`, `orders`, `order_items`, `stock_movements`.
- Alembic database migration environment with initial migration `001_initial_schema.py`.
- Validated starter-pack seed import script (`backend/scripts/seed_db.py`) and catalogue audit script (`backend/scripts/validate_catalogue.py`).
- Product CRUD, search (canonical name, brand, colloquial alias), and inventory endpoints.
- Enforce the non-negotiable business rule: customer confirmation creates a `pending` order without stock deduction; inventory is deducted only upon shopkeeper acceptance with an atomic stock recheck.
- Full pytest test suite with 100% pass rate.

#### 2. Rationale
The data layer is the authoritative backbone of DukaanSaathi. Voice AI understands customer intent, but the backend must control stock, enforce constraints, calculate authoritative totals, and guarantee transactional safety without overselling.

#### 3. Actions Performed
- **FastAPI Core Scaffolding:**
  - Implemented `backend/app/core/config.py` with Pydantic v2 `BaseSettings`, `.env` integration, and flexible CORS origin parsing.
  - Implemented `backend/app/core/database.py` with SQLAlchemy engine pooling, connection validation, and seamless fallback between PostgreSQL and SQLite.
  - Implemented `backend/app/core/security.py` protecting merchant administrative operations with Bearer tokens.
- **SQLAlchemy Domain Models (`backend/app/models/`):**
  - `Store`: Tenant store profile, unique slug, currency, timezone.
  - `Product`: SKU unique per store, non-negative price constraint, positive pack size, active toggle.
  - `ProductAlias`: Indexed normalized alias for fast phonetic lookups, cascade deletion on product drop.
  - `StoreInventory`: Non-negative stock and reserved constraints, low-stock threshold.
  - `Customer`: Customer identity and order session tracking.
  - `OrderSession`: Active/confirmed/expired state machine, jsonb draft cart.
  - `Order`: Pending/accepted/preparing/ready/completed/rejected/cancelled status machine, total amount constraint, rejection reason.
  - `OrderItem`: Snapshotted name, sale unit, unit price, and subtotal.
  - `StockMovement`: Authoritative ledger of every stock modification (`change_quantity`, `reason`).
- **Alembic Migrations:**
  - Created `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`.
  - Authored `backend/alembic/versions/001_initial_schema.py` covering all 9 tables, foreign keys, indexes, and check constraints.
- **Data Validation & Seeding (`backend/scripts/`):**
  - Implemented `seed_db.py`: Pre-flight validates all 100 products, 306 aliases, and 100 inventory records before write; idempotently upserts records.
  - Implemented `validate_catalogue.py`: Audits database constraints, inventory foreign keys, and low-stock indicators.
- **REST API Endpoints (`backend/app/api/v1/`):**
  - `GET /api/v1/products`: Paginated product catalogue with category and active filters.
  - `GET /api/v1/products/search`: Multi-strategy search across canonical names, brands, and colloquial aliases with match source attribution.
  - `GET /api/v1/products/{id}`: Product detail with inventory and alias resolution.
  - `POST /api/v1/products`: Merchant-protected product creation with initial stock and aliases.
  - `PUT /api/v1/products/{id}`: Merchant-protected product attribute and price updates.
  - `DELETE /api/v1/products/{id}`: Soft-deactivation.
  - `GET /api/v1/inventory`: Inventory dashboard with low-stock/out-of-stock filtering.
  - `PUT /api/v1/inventory/{id}`: Merchant-protected stock adjustment with automatic `StockMovement` logging.
  - `POST /api/v1/orders`: Customer confirmation endpoint creating `pending` orders with snapshotted prices; verifies zero stock deduction.
  - `GET /api/v1/orders`: Merchant order feed with status filtering.
  - `POST /api/v1/orders/{id}/accept`: Merchant acceptance endpoint performing atomic stock recheck, decrementing inventory, and logging `StockMovement`.
  - `POST /api/v1/orders/{id}/reject`: Merchant rejection endpoint recording reason without touching inventory.
- **Pytest Suite (`tests/backend/`):**
  - Configured `tests/backend/conftest.py` with in-memory SQLite and `StaticPool` for test isolation.
  - Authored 17 comprehensive unit and integration tests across models, product APIs, inventory management, order lifecycle, atomic rollbacks, and seed validation.

#### 4. Issues Encountered & Fixes Applied
1. **CORS List Parsing in Pydantic Settings:** `ALLOWED_ORIGINS` in `.env` was a plain string; added a robust `@field_validator` in `config.py` supporting comma-separated strings, JSON arrays, and single URLs.
2. **PostgreSQL Localhost Daemon Unreachable:** When local PostgreSQL daemon is not active on port 5432, `database.py` catches `OperationalError` gracefully, logs a clear warning, and routes to local SQLite (`dukkaansaathi_dev.sqlite`) for development without blocking execution.
3. **SQLite In-Memory Test Isolation:** Default SQLite in-memory connections are connection-isolated, causing tables created in test setup to disappear in subsequent sessions. Configured SQLAlchemy `StaticPool` in `conftest.py`, ensuring all test transactions share the same in-memory schema.
4. **Starter Pack Verification Assertions:** `PRD001` in the synthetic starter pack is `"Loose Wheat Flour (Atta)"` rather than Aashirvaad (which is `PRD002`). Updated test assertion to verify `Atta` on `PRD001` and `Aashirvaad` on `PRD002`.
5. **Transient Test Artifacts Hygiene:** Added `*.sqlite`, `*.sqlite3`, and `*.db` to `.gitignore` (excluding `data/database/dukkaansaathi_seed.sqlite`), adhering strictly to the clean workspace mandate.

#### 5. Verification Results
- **Pytest Execution:** 17 tests executed, 17 passed, 0 failed, 0 skipped, 0 warnings (Execution time: 0.70s).
- **Catalogue Audit:** Verified 1 store, 100 products, 306 aliases, 100 inventory records, 0 negative stock/price violations.
- **Critical Business Rule Test:** Explicitly verified that `POST /api/v1/orders` creates orders in `pending` status without deducting inventory, and `POST /api/v1/orders/{id}/accept` atomically validates and decrements stock.
- **Phase 2 Completion Gate:** Fully passed.

---

## 5. Current Repository & Asset Inventory

```
C:\Users\hiten\Downloads\gnani
│   .env (ignored)
│   .env.example
│   .gitignore
│   DukaanSaathi_Phase_0_PRD_v1.0.md
│   pytest.ini
├───backend
│   │   __init__.py
│   │   alembic.ini
│   ├───alembic
│   │   │   env.py
│   │   │   script.py.mako
│   │   └───versions
│   │           001_initial_schema.py
│   ├───app
│   │   │   __init__.py
│   │   │   main.py
│   │   ├───api
│   │   │   │   deps.py
│   │   │   │   __init__.py
│   │   │   └───v1
│   │   │           inventory.py
│   │   │           orders.py
│   │   │           products.py
│   │   │           router.py
│   │   │           __init__.py
│   │   ├───core
│   │   │       config.py
│   │   │       database.py
│   │   │       security.py
│   │   │       __init__.py
│   │   ├───models
│   │   │       base.py
│   │   │       customer.py
│   │   │       inventory.py
│   │   │       order.py
│   │   │       product.py
│   │   │       stock_movement.py
│   │   │       store.py
│   │   │       __init__.py
│   │   └───schemas
│   │           common.py
│   │           inventory.py
│   │           order.py
│   │           product.py
│   │           __init__.py
│   └───scripts
│           seed_db.py
│           validate_catalogue.py
├───data
│   │   PACK_CONTENTS.json
│   │   README.md
│   ├───audio
│   │       README.md
│   │       recording_manifest.csv
│   ├───data
│   │       categories.csv
│   │       conversation_scenarios.json
│   │       inventory.csv
│   │       products.csv
│   │       products.json
│   │       product_aliases.csv
│   │       product_aliases.json
│   │       store.json
│   │       voice_test_cases.csv
│   │       voice_test_cases.json
│   ├───database
│   │       dukkaansaathi_seed.sqlite
│   │       schema_postgres.sql
│   ├───docs
│   │       data_dictionary.md
│   │       evaluation_protocol.md
│   │       sample_api_payloads.json
│   └───scripts
│           seed_postgres.py
├───docs
│       PHASE_1_FEASIBILITY_REPORT.md
│       PRD.md
│       PROJECT_CHRONICLE.md
└───tests
    ├───backend
    │       conftest.py
    │       test_database_models.py
    │       test_inventory_api.py
    │       test_orders_and_business_rules.py
    │       test_products_api.py
    │       test_seed_validation.py
    └───gnani
            test_prisma.py
            test_timbre.py
```

---

## 6. Current State & Immediate Next Steps

### Current State
- **Phase 0 (Requirements & PRD):** Complete & frozen.
- **Phase 1 (Gnani Prisma & Timbre Feasibility):** Complete & validated on live endpoints.
- **Phase 2 (Product Architecture & Data Foundation):** Complete & verified with 17 passing automated tests. All 100 products, 306 aliases, and inventory records loaded with full constraint verification.

### Immediate Next Steps (Phase 3: Core Order Intelligence Engine)
1. **Transcript Normalization Service:** Build phonetic mapping for colloquial Hinglish terms (*aata* $\rightarrow$ *atta*, *cheeni* $\rightarrow$ *sugar*, *doodh* $\rightarrow$ *milk*).
2. **Multi-Strategy Product Matcher:** Implement exact, alias, and fuzzy candidate resolution with RapidFuzz.
3. **Quantity & Packaging Parser:** Extract metric and colloquial quantities (*aadha kilo*, *pao bhar*, *do packet*) with packaging integrity checks.
4. **Conversational State Machine:** Implement dialogue state transitions (`COLLECTING`, `NEEDS_CLARIFICATION`, `AWAITING_CONFIRMATION`, `ORDER_PLACED`).
5. **Multi-turn Order Corrections:** Support conversational additions, removals, and quantity overrides against the authoritative database.
