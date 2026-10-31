# MARSEL ROAPP — UNIFIED MASTER CONTROL — 2026-09-02

## 1. Canonical identity

- System: **MARSEL ROAPP**
- Business contour: **Ювелирная студия MARSEL**
- Technology contour: **ROAPP**
- Canonical repository: `atalanrafael-jpg/MARSEL-ROAPP`
- Canonical branch: `main`
- Canonical live audit: `.github/workflows/marsel-unified-control-plane.yml`
- Historical material: `старые данные/`

## 2. Source-of-truth hierarchy

1. Current `main` repository state.
2. Fresh GitHub Actions evidence tied to current `main`.
3. Direct live RO App evidence and artifacts.
4. Current authoritative RO App documentation.
5. Historical files/chats only as context; never as current truth.

## 3. System structure

`MARSEL` business processes → `ROAPP` technical control → `GitHub main` source → `Actions/evidence/gates` verification.

There must be one production/control plane. Supporting workflows may exist only when their responsibility is distinct and registered; they must not create a second live audit path.

## 4. Safety invariant

`READ_ONLY` is the default. Production WRITE is blocked.

Required sequence before any production mutation:

`READ → ANALYZE → BACKUP → RESTORE CHECK → RECONCILIATION → DRY-RUN → IDEMPOTENCY → ROLLBACK → SAFETY GATE → CONTROLLED WRITE → POST-WRITE VERIFY`

No deletion or mass mutation is automatic. No undocumented endpoint, guessed identifier or synthetic evidence may be promoted to PASS.

## 5. Current verified baseline

Historical direct evidence confirms:

- RO App `GET /orders` worked with HTTP 200 in READ-ONLY mode.
- A historical order audit checked 4,373 orders with unique IDs and no missing client/status fields in that run.
- A deeper READ-ONLY audit recorded 6,820 successful detail requests with zero detail failures.
- API inventory and data-quality audit infrastructure exists in the canonical repository.
- Current repository safety rules keep production WRITE disabled.

These figures are evidence for their respective runs, not claims about a perpetual current database count.

## 6. P0 — launch blockers

### P0.1 Backup + restore
Direct full permitted backup/export and an independently verified restore/integrity test are required.

### P0.2 Current API/entity completeness
Reconcile the current authoritative API documentation against the canonical registry and verify required entities with safe live GETs.

### P0.3 Warehouse contract
The current official RO App API reference (v2.0.1) documents `GET https://api.roapp.io/v2/warehouse/`. It documents:
- `type`: optional; defaults to `product`; allowed values are `product` and `asset`.
- `branch_id`: optional location identifier.

The canonical diagnostic `scripts/marsel_warehouse_contract_v20_48.py` uses this documented path and probes only the two documented `type` values. On 2026-10-30, both live READ_ONLY probes returned HTTP 404. Therefore, the code path matches the currently published API reference, but the live warehouse contract is **NOT_VERIFIED**. The 404 cause is **NOT_VERIFIED**; do not switch to an undocumented alternative path or guess a `branch_id`. The next diagnostic must use an authorized, documented read-only request and confirm the account's API access with RO App support if the 404 persists. No warehouse data or production configuration was changed.

### P0.4 Production gate evidence inventory
Required evidence must be real, current and traceable; missing evidence remains `REVIEW_REQUIRED`.

### P0.5 Security credential remediation
Complete direct evidence for rotation/remediation of the historical credential-exposure issue and verify no real credential remains in repository/history/logs/artifacts.

## 7. P1 — operational readiness

- Product-code collision/reference review without automatic deletion.
- Gmail OAuth read-only authorization test.
- Official RO App MCP authorization test.
- GitHub account/ruleset/secret-scanning/push-protection verification where account-level controls are required.
- Reconciliation of supporting workflows so every workflow has one registered responsibility.
- Master Agent runtime implementation and deterministic evidence/checkpoint tests.

## 8. P2 — growth and automation

After safety gates are closed:

- repair/customer follow-up automation;
- catalog and inventory automation;
- marketplace/e-commerce synchronization;
- KPI and financial reporting;
- AI-assisted operational queues;
- content and lead workflows;
- controlled integrations.

## 9. Cleanup policy

- Do not delete historical evidence.
- Do not delete issues merely because they are old; consolidate only after checking dependencies and preserving traceability.
- Do not keep multiple active implementations of the same control responsibility.
- Versioned scripts remain only when referenced by an active dependency; otherwise archive after dependency removal and fresh CI verification.
- All canonical links must use `atalanrafael-jpg/MARSEL-ROAPP`.

## 10. Completion definition

The project is **GO** only when all required P0 gates have fresh direct evidence and the Production Gate passes. A green CI run alone is insufficient.

Until then:

`STATUS = REVIEW_REQUIRED / NO-GO FOR PRODUCTION WRITE`

## 11. Execution loop

`OBSERVE → MEASURE → FIND → FIX → TEST → VERIFY → DOCUMENT → MONITOR`

Every material change produces evidence and a new checkpoint. Continue from the newest verified checkpoint; do not restart completed work without cause.
