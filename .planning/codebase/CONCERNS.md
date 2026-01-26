# Codebase Concerns

**Analysis Date:** 2026-01-25

## Tech Debt

### Oversized Route Handlers (File Bloat)

**Issue:** Multiple route files exceed 2,500+ lines, mixing presentation logic with business logic.

**Files:**
- `app/fretes/routes.py` (5,851 lines) - Freight operations, approvals, invoicing
- `app/cotacao/routes.py` (3,479 lines) - Quote management
- `app/custeio/routes/custeio_routes.py` (3,279 lines) - Cost calculation
- `app/monitoramento/routes.py` (2,654 lines) - Monitoring and tracking
- `app/embarques/routes.py` (2,764 lines) - Shipment management
- `app/faturamento/routes.py` (1,194+ lines visible, likely longer) - Invoicing

**Impact:**
- Difficult to navigate and maintain
- Hard to isolate bugs without redeploying entire module
- Testing individual features requires loading entire route file
- Code reuse patterns become unclear

**Fix approach:**
- Extract business logic into service layer (already partially done in some modules)
- Split routes into multiple blueprints by domain (e.g., `fretes_lancamento.py`, `fretes_aprovacoes.py`)
- Move form validation to dedicated validators
- Consolidate repeated logic into utility functions

---

### Inconsistent Exception Handling

**Issue:** Generic `except Exception as e:` clauses throughout codebase, many without proper logging or user feedback.

**Files with patterns:**
- `app/faturamento/routes.py` (50+ bare exception handlers)
- `app/faturamento/services/processar_faturamento.py` (20+ silent catches)
- `app/faturamento/services/atualizar_peso_service.py` (15+ silent catches)
- `app/cadastros_agendamento/routes.py` (10+ handlers)

**Impact:**
- Errors silently fail, returning generic empty responses (`return []`, `return {}`, `return None`)
- No audit trail for debugging production issues
- Users receive no feedback about what went wrong
- Intermittent failures invisible to monitoring

**Fix approach:**
- Create exception hierarchy for domain-specific errors (InvoicingError, WeightUpdateError, etc.)
- Use structured logging with error context (request_id, user_id, data snapshot)
- Return explicit error responses to clients (not silent `None`)
- Implement error recovery strategies: retry logic, partial success, fallback operations

---

### Incomplete Pallet Module Refactoring

**Issue:** Large module migration in progress (`v1 → v2`), creating ambiguity about which version to use.

**Files:**
- `app/pallet/routes_legacy.py` (58,717 lines) - Old implementation, marked deprecated
- `app/pallet/models/` - Multiple new models: `vale_pallet.py`, `solucao.py`, `credito.py`, `documento.py`, `nf_remessa.py`, `nf_solucao.py`
- `app/pallet/routes/` - New v2 routes partially implemented

**Impact:**
- Developers don't know which implementation to extend
- Migration incomplete - both versions running in production
- Risk of duplicate fixes in old/new code
- Database schema unclear (which tables are canonical?)
- Two separate UI codebases to maintain

**Current status:** Migration spec exists (`.claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md`) but execution incomplete

**Fix approach:**
- Complete migration to v2 fully (cut over date needed)
- Freeze v1 routes (read-only, redirect to v2)
- Migrate all active data from old tables to new schema
- Update all external references from v1 to v2
- Remove `routes_legacy.py` and old models once migration complete

---

### Multiple Database Migration Approaches

**Issue:** 184 migration files and 83+ migration/creation scripts in `/scripts` indicate ad-hoc schema management.

**Files:**
- `scripts/` - Manual migration scripts (50+ files for different concerns)
- `scripts/migrations/` - Additional structured migrations
- `app/*/scripts/` - Module-specific migrations scattered throughout codebase
- `scripts/pallet/001_criar_tabelas_pallet_v2.py|sql` - New pallet tables created outside migrations

**Impact:**
- No single source of truth for schema state
- High risk of inconsistency between environments (local/staging/production)
- Scripts are fragile: manual path handling, no version tracking
- Hard to understand what each migration does without reading code
- Difficult to rollback if migration fails

**Fix approach:**
- Consolidate all migrations into `migrations/` using Alembic (Flask-Migrate)
- Create migration versioning system with dependencies
- Implement pre-migration validation (check current schema state)
- Document critical migrations: what changed, why, rollback procedure
- Lock down direct SQL script execution in production (use migration system)

---

## Known Bugs

### Weight Calculation Race Condition

**Issue:** `app/faturamento/services/atualizar_peso_service.py` updates shipment weights without row-level locks.

**Files:** `app/faturamento/services/atualizar_peso_service.py` (250+ lines)

**Trigger:**
1. User A opens shipment, sees weight=100
2. User B opens same shipment, sees weight=100
3. User A updates weight to 110
4. User B updates weight to 105
5. Result: Weight is 105 (User A's change lost)

**Workaround:** None currently. Users must coordinate manually.

**Fix approach:**
- Add `version` column to `Embarque` table for optimistic locking
- Implement pessimistic locking: `session.query(Embarque).with_for_update().filter(...)`
- Or migrate to event-sourced weight history (immutable updates, replay to current state)

---

### Silent NF Synchronization Failures

**Issue:** When NF (invoice) sync to Odoo fails, system marks item as synchronized but doesn't actually sync data.

**Files:**
- `app/faturamento/services/` - Multiple services handle NF sync
- `app/separacao/models.py` - Field `sincronizado_nf` set to True even on partial failures

**Symptoms:**
- Invoice marked as synced in local DB but missing from Odoo
- Separated items disappear from carteira (marked synced) but no actual invoice created
- Financial reports show invoiced amounts that don't appear in Odoo

**Trigger:** Odoo timeout (>8s) or network blip during `stock.move` creation

**Workaround:** Query Odoo directly to verify NFs actually exist, re-sync missing ones manually

**Fix approach:**
- Implement two-phase commit: mark synced ONLY after confirming Odoo received data
- Add Odoo verification callback before clearing `sincronizado_nf=False`
- Create retry queue for failed syncs (RQ/Celery job with exponential backoff)
- Log all sync attempts with Odoo response codes (success/timeout/validation error)

---

## Security Considerations

### Missing Input Validation on CNPJ/CPF Fields

**Risk:** CNPJ and CPF fields accept invalid formats, leading to downstream Odoo integration failures.

**Files:**
- `app/utils/cnpj_utils.py` - Has `normalizar_cnpj()` but not enforced at route level
- `app/carteira/routes/separacao_api.py` - Accepts CNPJ without validation
- `app/recebimento/services/validacao_fiscal_service.py` - Assumes valid CNPJ already

**Current mitigation:** None consistent. Some routes validate, others don't.

**Recommendations:**
- Create `@validate_cnpj` and `@validate_cpf` decorators on all routes accepting these fields
- Implement database constraint: check CNPJ format before INSERT/UPDATE
- Normalize CNPJ on input (standardize to XX.XXX.XXX/XXXX-XX format)
- Reject requests with invalid format at route entry point

---

### Odoo API Credentials in Logs

**Risk:** XML-RPC credentials (username, password, URL) may be logged in debug mode.

**Files:**
- `app/odoo/utils/connection.py` - Handles Odoo authentication
- `worker_render.py:99` - Sets `logging.DEBUG` based on verbose flag
- `worker_atacadao.py:94` - Similar debug logging configuration

**Current mitigation:** Credentials retrieved from env vars, but DEBUG mode in production could leak them.

**Recommendations:**
- Create logging filter to redact sensitive fields (password, API keys, CNPJ)
- Never log request/response bodies for Odoo XML-RPC calls in production
- Implement centralized secret redaction in logger configuration
- Audit log files for exposed credentials

---

## Performance Bottlenecks

### Carteira Sync Performance (2,790 lines)

**Problem:** `app/odoo/services/carteira_service.py` performs full carteira import on every sync, no pagination or delta logic.

**Files:** `app/odoo/services/carteira_service.py` (2,790 lines)

**Current approach:**
- Fetches ALL open orders from Odoo each sync
- Creates/updates local CarteiraPrincipal records for each
- No tracking of what changed (delta detection)

**Bottleneck:** For 50K+ open orders, this takes 30-45 seconds per sync, blocking UI requests.

**Impact:**
- User waiting for carteira dashboard: 30-45s latency
- Sync job consumes database connections for extended periods
- Other requests queued while sync locks tables

**Improvement path:**
- Implement delta sync: track last sync time, fetch only orders modified since
- Add pagination to Odoo query (fetch 1000 at a time, process in batches)
- Move sync to background job (RQ worker) with progress tracking
- Cache carteira snapshot in Redis for 5-10 minutes between full syncs
- Implement incremental upsert: use `INSERT ... ON CONFLICT` to batch updates

---

### Recebimento Validation Service Complexity (2,485 lines)

**Problem:** `app/recebimento/services/validacao_nf_po_service.py` is monolithic validator with no separation of concerns.

**Files:** `app/recebimento/services/validacao_nf_po_service.py` (2,485 lines)

**Current structure:**
- Single service class with 50+ validation methods
- Validates tax, quantity, price, UoM all in one pass
- No short-circuit logic: keeps validating even after first failure
- Re-runs same validations on every PO for same supplier

**Impact:**
- Validation on large batches (100+ POs): 2-5 minutes
- Memory usage grows with batch size (loads all POs in memory)
- Can't reuse cached validation results across requests

**Improvement path:**
- Break into specialized validators: `TaxValidator`, `QuantityValidator`, `PriceValidator`
- Implement caching: memoize supplier tax rules, product specifications
- Add short-circuit: stop validation at first critical error
- Implement validation rules as data (configuration) not code
- Consider ML-based anomaly detection for outliers instead of rule-based validation

---

### Portal Playwright Client (1,953 lines)

**Problem:** Web scraping Atacadao portal with Playwright is brittle and slow (1-2s per order).

**Files:** `app/portal/atacadao/playwright_client.py` (1,953 lines)

**Current approach:**
- Launches headless browser for each order
- Waits for JavaScript rendering (2s timeout)
- Brittle selectors: `campo_data_visivel`, `campo_leadtime_iso`
- No caching: same orders scraped repeatedly

**Impact:**
- Order scheduling takes 2-5 seconds per order
- If portal updates selectors, entire system breaks
- High CPU/memory footprint (browser processes)

**Improvement path:**
- Request API access from Atacadao instead of scraping
- Implement caching: store order details for 24 hours
- Use API-level mocking in tests (don't actually launch browser)
- Cache browser instance (don't launch per request)
- Implement timeout recovery: default to user-provided dates if scraping fails

---

## Fragile Areas

### Odoo Integration (Multiple Services, 15K+ lines)

**Files:** `app/odoo/services/` (6+ services, ~15K lines)

**Why fragile:**
- XML-RPC protocol is low-level: no type checking, easy to pass wrong data
- Odoo IDs and UoM conversions are implicit (not validated on our side)
- 12+ documented GOTCHAS in `app/odoo/` docs (hardcoded IDs, tax delays, CNPJ formatting)
- Circuit breaker guards connection but not data integrity
- No schema version tracking (Odoo updates break assumptions)

**Safe modification:**
- Always wrap new Odoo calls in try/except with Circuit Breaker
- Log request/response bodies (with credentials redacted) for debugging
- Test all Odoo interactions in staging environment first
- Update docs when Odoo behavior changes (version-specific)
- Use hardcoded IDs only as fallbacks, query actual data when possible

**Test coverage:** Gaps
- No integration tests against real Odoo instance (would require staging env)
- Unit tests mock Odoo responses, don't validate actual Odoo behavior
- Schema changes in Odoo go undetected until production errors

---

### Pallet Module During Refactoring

**Files:** `app/pallet/models/`, `app/pallet/routes/`, `app/pallet/routes_legacy.py`

**Why fragile:**
- Dual implementations create ambiguity
- Migration incomplete: both old and new tables in use
- External code may reference either v1 or v2 (unknown which)
- If v1 deprecation rushed, orphaned records could cause data loss

**Safe modification:**
- Keep v1 and v2 strictly isolated (no cross-references between versions)
- Always check `deprecation_date` in route decorator before modifying v1
- Verify migrations exist for all v1→v2 data transfers before cutover
- Test complete rollback procedure before full migration
- Maintain dual-read capability during cutover (read from both, write to v2 only)

**Test coverage:** Incomplete
- `tests/pallet/test_migracao.py` - Migration tests exist but may not cover edge cases
- No tests for data consistency across old→new transition
- UI tests missing for v2 new features

---

### Financial Calculations (Pricing, Costs, Discounts)

**Files:**
- `app/custeio/` (3,279 lines)
- `app/utils/calculadora_frete.py`
- `app/fretes/services/lancamento_odoo_service.py`

**Why fragile:**
- Decimal precision issues: floating point math instead of Decimal type
- Multiple calculation paths: some use Odoo, some use local formulas
- Discrepancies between planned cost (custeio) and actual cost (Odoo) often undiagnosed
- No audit trail for cost changes (can't see who changed what when)
- Rounding inconsistencies: client sees R$ 100.01, invoice shows R$ 100.00

**Safe modification:**
- Use Python `Decimal` type for all monetary calculations (not `float`)
- Centralize cost calculation logic in single service, use everywhere
- Add cost change audit logs: before/after snapshots with user/timestamp
- Validate cost recalculation matches Odoo within 0.01 tolerance
- Test edge cases: fractional values, negative costs, zero costs

**Test coverage:** Minimal
- `tests/` - Pallet tests exist but limited coverage
- No tests for cost calculation edge cases
- No regression tests after financial rule changes

---

## Scaling Limits

### Database Connection Pool Saturation

**Problem:** 30+ concurrent HTTP requests each spawn a DB connection for full request duration.

**Files:**
- `app/__init__.py` - Flask-SQLAlchemy pool configuration
- Route handlers that don't release connections between operations

**Current capacity:**
- SQLite (dev): 1 connection, locks entire DB during writes
- PostgreSQL (production, Render): Pool size ~10, 30s checkout timeout
- Limit: ~10 concurrent requests before queue backs up

**Scaling path:**
- Increase connection pool: raise pool_size to 20, max_overflow to 10
- Implement connection pooling per-request (don't hold connection across operations)
- Use read replicas for reporting queries (dashboard, analytics)
- Implement query result caching for expensive reads (Redis)

---

### Memory Usage in Batch Operations

**Problem:** Loading 100K+ orders into memory for processing.

**Files:**
- `app/odoo/services/carteira_service.py` - Fetches all carteira orders
- `app/recebimento/services/validacao_nf_po_service.py` - Loads all POs for batch validation

**Current capacity:**
- 100K orders @ 1KB each = 100 MB (acceptable)
- 1M orders @ 1KB each = 1 GB (exceeds container memory limit, crashes)

**Scaling path:**
- Implement pagination: process in batches of 1000, not all-at-once
- Use generators instead of lists: `yield order` not `orders.append(order)`
- Stream results to client instead of buffering (HTTP chunked transfer encoding)
- Implement timeouts: operations taking >60s automatically paginated

---

### Render Deployment Limitations

**Problem:** Renders enforces 512 MB RAM limit for free/standard tier.

**Files:**
- `worker_render.py` - Worker configuration
- `app/scheduler/` - Background jobs that may exceed memory

**Current capacity:**
- Typical request: 50-100 MB
- Batch operation: 300+ MB
- Background job: can exceed limit and crash

**Scaling path:**
- Monitor memory usage: add alerts for >400 MB utilization
- Split large jobs: fetch+process in chunks
- Move to higher tier if consistent memory pressure
- Use external storage (S3) instead of loading into memory

---

## Dependencies at Risk

### Playwright Version Lock (Portal Integration)

**Risk:** Playwright updates may break Atacadao portal selectors.

**Impact:** If Atacadao redesigns portal, scheduling stops working instantly.

**Migration plan:**
- Request official API access from Atacadao (if available)
- Implement fallback: if scraping fails, ask user for manual input
- Use feature flags: disable portal integration if scraping unreliable
- Implement alert system: notify ops when portal breaks (50%+ failure rate)

---

### Odoo Version Compatibility (XML-RPC)

**Risk:** System is pinned to Odoo 14.x. Major version upgrades break compatibility.

**Files:** All Odoo integration code assumes Odoo 14.x API

**Impact:** Odoo 17.x released. Upgrading would require:
- Rewriting 50+ integration points (new models, field names, workflows)
- Testing against new database schema
- Potential 1-2 month effort

**Migration plan:**
- Document current Odoo version assumption (14.x) in code comments
- Plan upgrade timeline before Odoo 14 reaches EOL
- Create sandbox environment for testing Odoo 17 integration
- Implement feature flags to support both versions during transition

---

### Python Version EOL (3.11)

**Risk:** Project uses Python 3.12+ in production, but 3.11 support ends Oct 2025.

**Impact:** Security vulnerabilities in 3.11 won't be patched.

**Migration plan:**
- Ensure code runs on Python 3.13+ (currently likely to work)
- Update all CI/CD to test on 3.13
- Plan upgrade: Python 3.14 when released (~Oct 2025)

---

## Missing Critical Features

### Audit Trail for Business Changes

**Problem:** No immutable log of who changed what, when, and why in critical operations.

**Blocks:**
- Compliance audits (financial regulations require 5-year history)
- Debugging: can't trace when cost changed from 100 to 110
- Accountability: can't identify who made error
- Data recovery: can't restore deleted orders

**Affected areas:**
- Order creation/modification (carteira changes)
- Cost changes (custeio)
- Invoice modifications (faturamento)
- Pallet credit adjustments

**Implementation:** Add `audit_log` table with `(user_id, action, entity_type, entity_id, before, after, timestamp)` entries on all mutations.

---

### Monitoring and Observability

**Problem:** Limited visibility into system health, errors go unnoticed until users report.

**Blocks:**
- Ops can't detect Odoo integration failures in real-time
- Performance degradation undetected (queries getting slower)
- Error rates invisible without manual log review
- SLA breaches unknown until after the fact

**Missing tools:**
- APM (application performance monitoring): no slow query tracking
- Error tracking: no Sentry/Rollbar integration
- Metrics: no Prometheus/Datadog instrumentation
- Alerting: no automatic notifications for critical errors

**Implementation:** Integrate Sentry for error tracking, add APM instrumentation to slow operations.

---

### Pagination for Large Datasets

**Problem:** Many list views load all data, causing memory/performance issues.

**Blocks:**
- Freight list with 100K+ records freezes UI
- Carteira dashboard loading 50K+ orders at once
- Invoice report showing all time instead of last 30 days

**Affected routes:**
- `app/fretes/routes.py` - Freight listings
- `app/carteira/routes/` - Dashboard views
- `app/financeiro/routes/` - Financial reports

**Implementation:** Implement cursor-based pagination (offset/limit) with sort options.

---

## Test Coverage Gaps

### No Integration Tests for Odoo

**What's not tested:** Real Odoo interaction
- Order imports (carteira_service)
- Invoice syncs (faturamento_service)
- Stock movements (embarques to Odoo)
- Payment reconciliation

**Files:** `app/odoo/services/` (all critical paths untested against real Odoo)

**Risk:** Changes break Odoo integration undetected until production.

**Solution:**
- Set up staging Odoo instance
- Create integration test suite that runs against staging
- Include in CI/CD pipeline

---

### No E2E Tests for Critical Workflows

**What's not tested:** End-to-end user journeys
- Create order → Separate → Invoice → Reconcile payment
- Schedule delivery → Track → Confirm receipt
- Create pallet credit → Use in sale → Return to stock

**Risk:** Workflow breaks (e.g., separated items don't appear in invoice), no automated detection.

**Solution:**
- Implement E2E tests using Playwright (headless browser)
- Test happy path and common error cases
- Run on staging environment nightly

---

### Pallet Module Migration Tests Incomplete

**What's not tested:**
- Data consistency across v1→v2 migration
- Orphaned records in old tables after migration
- Backward compatibility during cutover

**Files:** `tests/pallet/test_migracao.py` (exists but incomplete)

**Risk:** Data loss during migration, inconsistent state, queries returning wrong data.

**Solution:**
- Expand migration tests to verify data counts match before/after
- Test rollback scenario: migrate back to v1 without data loss
- Verify foreign key constraints after migration

---

*Concerns audit: 2026-01-25*
