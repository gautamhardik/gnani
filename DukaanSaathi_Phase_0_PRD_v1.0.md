# DukaanSaathi — Phase 0 Product Requirements Document (PRD)

**Version:** 1.0  
**Date:** 30 October 2026  
**Status:** Working baseline — pending product-owner review  
**Target release:** 9 November 2026; competition submission by 10 November 2026, 11:59 PM IST

## Product promise
Customers can place a grocery order by speaking naturally in Hindi or Hinglish. The system converts speech into a structured cart, checks the store catalogue and stock, asks for explicit confirmation, and hands the order to the shopkeeper.

## 1. Product vision and summary
Make ordering from a neighbourhood kirana store as natural as speaking to the shopkeeper, while giving the shopkeeper a simple digital view of products, stock and incoming orders.

- **Product:** DukaanSaathi
- **Type:** Voice-first grocery ordering web application
- **Users:** Customer and kirana shopkeeper
- **Initial market:** One configured demonstration store in India
- **Primary languages:** Hindi and Hindi-English code-mixed speech (Hinglish)
- **Core AI:** Gnani Prisma (STT) and Gnani Timbre (TTS)
- **Business capability:** Product resolution, cart management, inventory validation and order handoff

The contest MVP is an order-capture and store-operations product. It does not promise real-time delivery, online payment, telephone IVR or multi-store commerce.

## 2. Problem and users
Small stores receive informal orders through conversations and messaging. Customers who prefer speaking may find conventional product-search interfaces inconvenient. Shopkeepers may need to manually interpret requests, check stock and reconstruct an order.

**Customer job:** Speak naturally, place an accurate order without typing every item, and understand price and availability.  
**Shopkeeper job:** Receive a clear itemized order, control inventory and process orders without re-entering the request.

## 3. Goals and measures

### MVP goals
1. Use Gnani Prisma in the real audio-to-transcript path.
2. Use Gnani Timbre to speak assistant responses in the customer workflow.
3. Convert Hindi/Hinglish requests into structured cart items.
4. Keep catalogue, stock and prices controlled by the backend/database.
5. Support clarification, quantity correction and item removal.
6. Require explicit customer confirmation before creating an order.
7. Provide shopkeeper inventory and order management.
8. Deploy a public working application.

### Proposed engineering targets
| Measure | Target |
|---|---:|
| Product identification accuracy | ≥90% |
| Quantity extraction accuracy | ≥90% |
| Exact cart match | ≥85% |
| Incorrect stock acceptance | 0 |
| Incorrect order total | 0 |
| Duplicate order from retry | 0 |
| Critical end-to-end tests | 100% pass |

These are internal targets, not official competition criteria or population-level claims. Report sample size and observed results.

## 4. Scope decisions
- One preconfigured demonstration store.
- Guest customer session; no customer registration.
- Protected shopkeeper login.
- Hindi/Hinglish are primary voice targets.
- Prisma and Timbre are mandatory; Evon is optional and cannot be a core dependency.
- PostgreSQL is the deployed source of truth.
- Each product variant/pack size is a separate sellable SKU.
- Prices and inventory come from the database, never from model-generated text.
- Customer confirmation creates a pending store order. Stock is deducted only when the shopkeeper accepts after an atomic stock recheck.
- No online payment, delivery integration, telephone IVR, WhatsApp, loyalty features or multi-store onboarding in the contest MVP.
- Seed products, aliases, prices and inventory are synthetic and must be labelled as such.

## 5. Core journeys

### Customer
1. Open the configured store and start a session.
2. Record a short Hindi/Hinglish request.
3. Backend sends audio to Prisma.
4. Order engine extracts products, variants, quantities and units.
5. Backend resolves each request against catalogue and inventory.
6. Ask for clarification when a product/variant/quantity is ambiguous.
7. Allow voice or manual cart correction.
8. Calculate total from database prices.
9. Speak and display itemized summary via Timbre and text UI.
10. Customer explicitly confirms or cancels.
11. Confirmed order is saved as `PENDING_STORE_ACCEPTANCE`.

### Shopkeeper
1. Sign in to protected merchant area.
2. Review pending order.
3. Accept/reject.
4. On acceptance, backend atomically rechecks stock and deducts it.
5. Move order through `ACCEPTED`, `PREPARING`, `READY`, `COMPLETED`, or `REJECTED`/`CANCELLED` as allowed.

## 6. Functional requirements
| ID | Requirement | Priority |
|---|---|---|
| FR-001 | Open the single configured store | P0 |
| FR-002 | Create guest session | P0 |
| FR-003 | Record, playback/retry and upload audio | P0 |
| FR-004 | Submit audio to Gnani Prisma | P0 |
| FR-005 | Display recognized transcript | P0 |
| FR-006 | Resolve transcript references to active catalogue SKUs | P0 |
| FR-007 | Ask clarification for ambiguous variants | P0 |
| FR-008 | Extract and normalize quantities/units | P0 |
| FR-009 | Add/remove/change cart items via voice or UI | P0 |
| FR-010 | Apply corrections to intended pending cart line | P0 |
| FR-011 | Check active status and current stock | P0 |
| FR-012 | Calculate totals from database prices | P0 |
| FR-013 | Clarify unknown/ambiguous references | P0 |
| FR-014 | Show itemized summary before confirmation | P0 |
| FR-015 | Require explicit customer confirmation | P0 |
| FR-016 | Persist confirmed order with item/price snapshots | P0 |
| FR-017 | Show order status by session/order reference | P0 |
| FR-018 | Generate spoken responses through Timbre | P0 |
| FR-019 | Text fallback if TTS fails | P0 |
| FR-020 | Protect merchant area and administrative APIs | P0 |
| FR-021 | Create/update/deactivate products | P0 |
| FR-022 | Update stock and prices with validation | P0 |
| FR-023 | View order queue | P0 |
| FR-024 | Recheck and deduct stock atomically on acceptance | P0 |
| FR-025 | Reject order with reason | P0 |
| FR-026 | Update order fulfilment status | P0 |
| FR-027 | Prevent duplicate confirmation effects | P0 |
| FR-028 | Accurately attribute Gnani models in demo/docs | P0 |
| FR-029 | Suggest available alternative | P1 |
| FR-030 | Use Evon for language interpretation, subject to feasibility | P1 |

## 7. Business rules
- Each variant/pack size is a distinct SKU.
- Aliases cannot override explicit brand, size or variant constraints.
- Packaged items use integer sellable units; loose goods may use decimal quantities only where the SKU allows it.
- Unit conversions must be explicit and dimensionally valid.
- Database prices, stock and SKU status are authoritative.
- If requested quantity is unavailable, explain the shortfall; do not silently substitute.
- Customer confirmation creates a pending order; stock is deducted on merchant acceptance after atomic revalidation.
- Order items preserve product/SKU/unit/quantity/price snapshots.
- Every stock change is recorded in stock movement history.
- No payment is collected in the MVP; placed does not mean paid or delivered.

## 8. Data and privacy
- Keep product identity separate from store-specific price and inventory. Core entities: `products`, `product_aliases`, `stores`, `store_inventory`, `order_sessions`, `orders`, `order_items`, `stock_movements` and `merchant_users`.
- 100 fictional demo-store products, aliases, synthetic prices and synthetic inventory.
- At least 30 short labelled voice utterances, recorded by consenting speakers; do not fabricate audio.
- Store expected transcript, SKU, quantity, unit and expected cart for evaluation.
- Do not retain raw audio by default; process and discard unless an explicit consent-based evaluation flow requires retention.
- Use synthetic customer records; collect minimum data; do not log secrets.

## 9. Non-functional requirements
- No order without explicit confirmation.
- No model-generated final price.
- Stock never becomes negative; acceptance and deduction are atomic.
- Retries do not duplicate orders or stock movements.
- Provisional p95 end-to-end voice-turn target: ≤12 seconds under defined demo conditions; measure and report actual results.
- Prisma failure: retry or manual text fallback. Timbre failure: visible text fallback.
- Mobile-first responsive UI, visible microphone/processing/speaking/error states, keyboard-accessible essential controls.
- API keys remain server-side; merchant APIs require authentication/authorization.
- Keep voice, order parsing, inventory, persistence and UI concerns separate.

## 10. Logical architecture
| Module | Responsibility |
|---|---|
| Next.js customer UI | Recording, transcript, cart, confirmation, status |
| Next.js merchant UI | Protected inventory and order operations |
| FastAPI | Session, validation, orchestration, response contracts |
| Prisma adapter | Audio submission and transcription response normalization |
| Order intelligence | Transcript normalization, item/quantity extraction, alias resolution, cart state |
| Inventory/order services | Stock validation, totals, order creation and transactional state changes |
| Timbre adapter | Response audio generation and failure handling |
| PostgreSQL | Source of truth for SKU, inventory, orders and status history |

**Stack:** Next.js, React, TypeScript, Tailwind CSS; Python, FastAPI, Pydantic; PostgreSQL, SQLAlchemy, Alembic; Gnani Prisma and Timbre; RapidFuzz as a candidate generator; Pytest; Vercel, Render and Neon.

## 11. End-to-end acceptance scenarios
1. Single in-stock product order produces correct SKU/quantity and database price.
2. Multi-product request creates separate correct cart lines.
3. Hindi/Hinglish alias maps correctly or asks for clarification.
4. Insufficient stock is explained and never silently accepted.
5. “Two” corrected to “one” updates the existing line.
6. Ambiguous pack sizes cause clarification.
7. Manual cart edits remain consistent with backend state.
8. No explicit confirmation means no submitted order.
9. Repeated confirmation creates one order only.
10. Stock change before merchant acceptance is rechecked.
11. Merchant acceptance deducts stock and updates order atomically.
12. Timbre failure retains text response and does not corrupt state.
13. Prisma failure causes retry/text fallback without invalid cart mutation.
14. Unauthorized inventory API request is rejected.
15. Rejected order has reason and no stock deduction.

## 12. Phase 0 exit criteria
- Vision, users and problem statement documented.
- MVP and out-of-scope items explicit.
- Customer and shopkeeper journeys documented.
- Requirements identified and prioritized.
- Business rules for SKU, quantity, pricing, stock and confirmation documented.
- Data, privacy, security and success measures documented.
- Acceptance scenarios defined.
- Product owner reviews this baseline and records any changes.

## 13. Phase 1 handoff
1. Verify Gnani account and credit balance.
2. Configure server-side API key without committing the secret.
3. Run and document Prisma smoke test.
4. Run and document Timbre smoke test.
5. Compare available Prisma versions on the same labelled Hinglish samples.
6. Verify current endpoint limits, supported formats and response schemas from official docs.
7. Measure credit consumption and latency.
8. Make an integration go/no-go decision.
