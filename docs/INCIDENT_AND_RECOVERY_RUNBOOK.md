# DukaanSaathi — Incident Management and Disaster Recovery Runbook

**Document Owner:** DevOps & Security Operations  
**Phase:** Phase 9 Production Readiness  
**Status:** Certified & Active  
**Last Updated:** 2026-10-31  

---

## 1. Incident Classification Framework

| Severity | Definition | Target Response (MTTR) | Examples |
| :--- | :--- | :--- | :--- |
| **SEV-1 (Critical)** | Core service down; voice turns failing; database unavailable; inventory oversell occurring. | $< 15\text{ minutes}$ | PostgreSQL daemon down; database corrupt; Gnani API credentials revoked. |
| **SEV-2 (Major)** | Degraded performance; Timbre TTS synthesis failing (text fallback active); rate limits tripping legitimately. | $< 1\text{ hour}$ | Upstream Timbre latency $> 5\text{s}$; high CPU on FFmpeg transcoding; merchant login slow. |
| **SEV-3 (Minor)** | Non-blocking issues; single SKU mapping mismatch; cosmetic UI flaw; minor log warning. | $< 24\text{ hours}$ | Alias lookup spelling gap; localized layout bug on rare viewport. |

---

## 2. Standard Operating Procedures (SOP)

### SOP-01: PostgreSQL Connection Failure & Failover
- **Trigger:** Health probe returns `HTTP 503` on `/health/ready`, or backend logs show `[DATABASE ERROR] Critical: Cannot connect to PostgreSQL`.
- **Immediate Action:**
  1. Inspect database daemon status:
     ```powershell
     # Windows local / staging
     Get-Process -Name postgres
     # Linux production / container
     systemctl status postgresql || kubectl get pods -l app=postgres
     ```
  2. If daemon stopped, restart service:
     ```powershell
     C:\Users\hiten\pgsql\bin\pg_ctl.exe -D C:\Users\hiten\pgsql\data -l pg.log restart
     ```
  3. Verify connection string in environment:
     ```powershell
     python -c "from backend.app.core.database import engine; print(engine.connect())"
     ```
  4. Ensure `APP_ENV=production` fails loudly and does **NOT** attempt SQLite fallback.

---

### SOP-02: Cold Restoration from PostgreSQL Backup Dump
- **Trigger:** Relational data corruption, accidental drop, or migration failure requiring full rollback.
- **Procedure:**
  1. Terminate all active FastAPI backend connections:
     ```sql
     SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'dukaansaathi' AND pid <> pg_backend_pid();
     ```
  2. Create a clean standby database:
     ```powershell
     $env:PGPASSWORD="<password>"
     psql -h <host> -U <user> -d postgres -c "DROP DATABASE IF EXISTS dukaansaathi_restored; CREATE DATABASE dukaansaathi_restored;"
     ```
  3. Restore from verified custom-format dump:
     ```powershell
     pg_restore -h <host> -U <user> -d dukaansaathi_restored -v <dump_file_path>.dump
     ```
  4. Verify relational integrity and table counts:
     ```sql
     SELECT 'products', count(*) FROM products
     UNION ALL
     SELECT 'inventory', count(*) FROM inventory
     UNION ALL
     SELECT 'product_aliases', count(*) FROM product_aliases;
     ```
     *Target: 100 products, 100 inventory rows, 306 aliases.*
  5. Swap database or update `DATABASE_URL` in `.env`.
  6. Restart backend and verify `GET /health` returns HTTP 200.

---

### SOP-03: Upstream Gnani STT/TTS Degradation or Outage
- **Trigger:** Latency alerts exceeding 5 seconds on Prisma STT or Timbre TTS; error rates $> 5\%$.
- **Expected System Behavior:**
  - **Prisma STT Failure:** Returns HTTP 400 with descriptive vernacular message: *"Maaf kijiye, aawaz sunne mein samasya aayi. Kripya dobara bole ya type karein."*
  - **Timbre TTS Failure:** Handled gracefully. Endpoint returns HTTP 200 with `audio_status="failed"`, intact cart snapshot, and full Hindi assistant text. Customer UI falls back to readable text message without crashing.
- **Recovery Actions:**
  1. Check Gnani provider status and API quota:
     ```powershell
     python tests/gnani/test_prisma.py
     python tests/gnani/test_timbre.py
     ```
  2. If provider is experiencing an extended outage, enable mock TTS synthesis:
     Set `FORCE_MOCK_VOICE=true` in environment to generate standard synthetic tones while keeping full order intelligence operational.
  3. Notify merchant dashboard of voice degradation mode.

---

### SOP-04: Concurrency Conflicts & Inventory Oversell Prevention
- **Trigger:** Merchant acceptance returns HTTP 409 Conflict.
- **Expected System Behavior:**
  - The atomic row locking mechanism (`with_for_update()`) ordered by `product_id` prevents circular deadlocks.
  - If two merchants or concurrent sessions attempt to accept an order for the last stock unit:
    - Order 1: Wins lock, stock decremented to 0.0, order status set to `accepted`, returns HTTP 200.
    - Order 2: Loses lock, detects `stock_quantity < item.quantity`, rejects acceptance with HTTP 409 Conflict, rollback executed, stock remains 0.0.
  - Zero stock oversell occurs.
- **Resolution:**
  1. Advise shopkeeper via dashboard toast: *"Stock khatam ho gaya hai. Kripya naya stock jodkar order dobara check karein."*
  2. Merchant can replenish stock via `PUT /api/v1/inventory/{product_id}`.

---

### SOP-05: Secret Leakage & Credential Rotation Protocol
- **Trigger:** Accidental leak of `GNANI_API_KEY`, `SHOPKEEPER_AUTH_TOKEN`, or `DATABASE_URL`.
- **Procedure:**
  1. **Immediate Revocation:**
     - Contact Gnani portal to rotate `GNANI_API_KEY`.
     - Generate a new cryptographic signing secret:
       ```python
       import secrets
       print("SECRET_KEY=" + secrets.token_urlsafe(32))
       print("SHOPKEEPER_AUTH_TOKEN=" + secrets.token_hex(24))
       ```
  2. **Update Environment:**
     - Update `.env` on backend server.
     - Never commit `.env` to Git.
  3. **Restart Backend Service:**
     - Restart FastAPI instances. Old merchant session tokens signed with the previous `SECRET_KEY` will immediately be rejected with HTTP 401, forcing re-authentication.
  4. **Post-Mortem & Audit:**
     - Run `git log -S "<leaked_secret>"` to verify the secret was not committed to version control.
     - Document in `docs/SECURITY_AUDIT_REPORT.md`.

---

## 3. Disaster Recovery Health Verification Checklist

Before closing any incident:
- [ ] `GET /health/live` returns HTTP 200 `{"status": "alive"}`
- [ ] `GET /health/ready` returns HTTP 200 `{"status": "ready"}`
- [ ] `GET /api/v1/merchant/overview` returns live metrics
- [ ] `POST /api/v1/orders` creates pending order with 0 stock deduction
- [ ] `POST /api/v1/orders/{id}/accept` verifies atomic stock decrement
- [ ] Logs show zero unmasked credentials or stack traces

