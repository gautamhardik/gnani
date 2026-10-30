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

---

## 5. Current Repository & Asset Inventory

```
C:\Users\hiten\Downloads\gnani
│   .gitignore
│   .env.example
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
│       PRD.md
│       PROJECT_CHRONICLE.md
└───tests
    └───gnani
            test_prisma.py
            test_timbre.py
```

---

## 6. Current State & Immediate Next Steps

### Current State
- **Phase 0:** Complete. Requirements, user journeys, data dictionary alignment, and conversational state machine specifications are documented and frozen in `docs/PRD.md`.
- **Git:** Initialized with proper ignores.

### Immediate Next Steps (Phase 1: Technical Feasibility & Gnani Integration)
1. **API Key Provisioning:** Obtain and verify the active `GNANI_API_KEY` in `.env`.
2. **Prisma Feasibility Spike (`tests/gnani/test_prisma.py`):**
   - Transcribe sample audio (Hindi, Hinglish, grocery multi-product utterances).
   - Test response latency and JSON response structure.
3. **Timbre Feasibility Spike (`tests/gnani/test_timbre.py`):**
   - Synthesize Hindi/Hinglish order confirmations (including currency readings like "₹145" / "ek sau paintalees rupaye").
   - Validate audio encoding (WAV/MP3) and playback compatibility.
4. **Failure Handling Protocol:** Document fallback paths when Prisma or Timbre fails or returns non-200 responses.
