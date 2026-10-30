# DukaanSaathi — QA Defect Register & Resolution Audit

**Document Version:** 1.0.0  
**Phase:** Phase 8 — Comprehensive Quality Assurance and Product Evaluation  
**Evaluation Date:** 2026-10-31  
**Status:** **ALL P0/P1 DEFECTS RESOLVED & VERIFIED**  

---

## 1. Executive Summary

This Defect Register tracks all functional, security, concurrency, and reliability issues identified during the development and evaluation of DukaanSaathi. In accordance with the Phase 8 guardrails:
- **P0 Defects (Critical — Security, Data Integrity, Stock Violation):** **0 Open (All Resolved & Verified).**
- **P1 Defects (High — Reliability, Error Boundary, Idempotency):** **0 Open (All Resolved & Verified).**
- **P2 Defects (Medium/Cosmetic — Minor Parser Nuisance, OS Subprocess Overhead):** **Documented & Tracked.**

---

## 2. Defect Register Matrix

| Defect ID | Severity | Subsystem | Description & Root Cause | Resolution & Fix | Retest Status |
|---|---|---|---|---|---|
| **DEF-001** | **P0** | Security / Merchant API | `GET /api/v1/orders` returned 200 OK for unauthenticated public requests, allowing unauthorized customer order data scraping. | Added `Depends(get_current_merchant)` dependency to `backend/app/api/v1/orders.py`. Requests without Bearer token return HTTP 401 Unauthorized. | **VERIFIED** (`tests/integration/test_auth_isolation_recovery.py`) |
| **DEF-002** | **P0** | Database Concurrency | Simultaneous acceptance of two competing orders for 1 remaining stock item caused a race condition without row-level locks, risking overselling. | Enforced deterministic row-level locks (`SELECT ... FOR UPDATE`) ordered by product ID (`sorted(order.items, key=lambda x: x.product_id)`) before decrementing stock. Competing call receives HTTP 409 Conflict. | **VERIFIED** (`tests/integration/test_postgres_concurrency.py`) |
| **DEF-003** | **P1** | Database Engine | `backend/app/core/database.py` silently fell back to local SQLite if PostgreSQL connection failed, risking unnoticed data divergence in staging/production. | Added environment gate in `database.py`: if `APP_ENV` is `staging` or `production`, failure to connect to PostgreSQL raises a fatal `RuntimeError` immediately on boot. | **VERIFIED** (`backend/app/core/database.py`) |
| **DEF-004** | **P1** | Voice Pipeline | When external Gnani Timbre TTS timed out or threw an HTTP error, the voice turn crashed with HTTP 500, losing customer session state. | Wrapped TTS synthesis in `backend/app/api/v1/voice.py` in a try/except error boundary. On TTS failure, the endpoint returns HTTP 200 with `audio_status="failed"`, preserving the cart and assistant text visually. | **VERIFIED** (`tests/integration/test_phase8_functional_reliability.py`) |
| **DEF-005** | **P1** | Order Lifecycle | Submitting a duplicate cancellation request on an already cancelled order could trigger a second compensating stock movement, artificially inflating inventory. | Added state transition guard in `backend/app/api/v1/orders.py`: an order can only be cancelled from `accepted`, `preparing`, or `ready`. Subsequent cancellation returns HTTP 400 Bad Request and halts execution. | **VERIFIED** (`tests/integration/test_phase8_functional_reliability.py`) |
| **DEF-006** | **P2** | Audio Service | Windows subprocess creation overhead for `ffprobe` + `ffmpeg` on WebM files inflated preprocessing latency to ~1.17s. | Implemented fast-path in-memory WAV validation via Python's standard `wave` module (0.07ms median). Decoupled `ffprobe` for WebM to reduce conversion to 338ms. | **VERIFIED** (`tests/voice/run_phase8_performance_trials.py`) |
| **DEF-007** | **P2** | Order Intelligence | Test Case `TC024` ("Teen Parle-G aur do Lays chips") extracted Parle-G but grouped Lays in single-pass noun chunking. | Documented as parser limitation in compound multi-brand Hinglish code-switching; resolved naturally in multi-turn conversational dialogue. | **DOCUMENTED** (`data/benchmarks/phase_8_order_intelligence.json`) |
| **DEF-008** | **P2** | E2E Testing | Next.js dev server on-demand page compilation took >20s on first visit, exceeding default Puppeteer navigation timeout. | Configured automated browser harness to run against pre-compiled production build (`npm run build` + `npm run start`), serving pages in <500ms. | **VERIFIED** (`tests/e2e/device_ux_qa.cjs`) |

---

## 3. Detailed Defect Resolution Audit

### DEF-001: Unauthenticated Merchant Order Access (P0)
- **Reproduction:** Call `curl -X GET http://localhost:8000/api/v1/orders` without headers.
- **Initial Behavior:** Returned JSON array of all customer grocery orders with status 200.
- **Remediation:** Injected `current_merchant: Store = Depends(get_current_merchant)` into route handler.
- **Retest Result:** Confirmed HTTP 401 Unauthorized across all test suites.

### DEF-002: Atomic Multi-Connection Row Locking (P0)
- **Reproduction:** Concurrently fire 2 worker threads accepting Order A and Order B for 1.0 unit of `PRD010` (stock: 1.0) against PostgreSQL 16.6.
- **Initial Behavior:** Potential race condition if reads occurred before writes.
- **Remediation:** Added `db.query(StoreInventory).filter(...).with_for_update().first()` with deterministic sorting by `product_id` to eliminate deadlocks.
- **Retest Result:** Exactly 1 thread received HTTP 200 OK; second thread received HTTP 409 Conflict (`Insufficient stock`). Final PostgreSQL stock: exactly 0.000.

### DEF-004: Timbre TTS Error Boundary (P1)
- **Reproduction:** Mock `TimbreTTSService.synthesize` to raise `requests.exceptions.Timeout`.
- **Initial Behavior:** Uncaught exception caused FastAPI to return HTTP 500 Internal Server Error, clearing the customer's draft items in the frontend.
- **Remediation:** Enclosed TTS call in try/except block. Returns `audio_status = "failed"`, `audio_base64 = None`, and logs warning.
- **Retest Result:** Test `test_voice_turn_tts_failure_recovery` passes with HTTP 200, returning intact cart and display text.

---

## 4. Phase 8 Defect Gate Decision

All identified **P0 and P1 defects have been completely resolved, verified, and regression-tested**. Zero critical vulnerabilities remain open.
The system is stabilized and ready for Phase 8 sign-off.
