# MARSEL ROAPP — MASTER PROJECT CONTROL

## Purpose
Единая контрольная точка проекта: техническое состояние RO App integration, качество данных, безопасность, бизнес-автоматизация, deployment и коммерческий контур MARSEL.

## Canonical state — 2026-09-09
- Repository: `atalanrafael-jpg/MARSEL-ROAPP`
- Branch: `main`
- Current repository `main` HEAD: `238d1c7121d902ae3bdacf59b33525b585c79090`.
- Latest commit: `security: harden MARSEL ROAPP connector boundary`.
## Canonical state — 2026-09-20
- System: **MARSEL ROAPP** — единая каноническая система.
- Repository: `atalanrafael-jpg/MARSEL-ROAPP`
- Technical canonical branch: `main`
- Repository default branch: `main`.
- Current repository `main` checkpoint recorded by this control document: **historical** `75e4648e898cbc12e5bb517e5256685c2ca1385b`.
- Canonical control plane: `.github/workflows/marsel-unified-control-plane.yml`
- Canonical control contract: `01_MASTER/MARSEL_ROAPP_CONTROL_PLANE_V2.md`
- ChatGPT operating protocol: `docs/MARSEL_CHATGPT_OPERATING_PROTOCOL.md`
- Repository validator: `scripts/marsel_control_plane_validate.py`
- Current integration mode: READ-ONLY.
- Owner MVP vertical slice is present in `web/index.html`, served at `/app`, with Supabase Auth/RLS integration.
- Production WRITE: DISABLED.

## Latest verified CI
- Earlier verified application/code checkpoint `c84825442857bb9cc51585093bac68d338fac7d1` had successful test/control-plane runs.
- Current `main` has since advanced to `238d1c7121d902ae3bdacf59b33525b585c79090`, including connector-boundary security hardening and security regression tests.
- A successful CI result on an earlier checkpoint does not prove the current HEAD is production-ready.
- Current HEAD requires fresh CI verification before being treated as a fully verified application checkpoint.

## Canonical state — 2026-09-24
- Repository: `atalanrafael-jpg/MARSEL-ROAPP`
- Branch: `main`
- Verified current repository HEAD via GitHub commit search: `c76957d86da6866357182aa67c4c4589a282829d`.
- HEAD commit: merge of PR #156, `docs: reconcile MARSEL ROAPP master control with current main`.
- Current commit status is `pending` with zero reported statuses; this does not establish CI success.
- Production WRITE remains disabled.

## Evidence precedence
1. Current `main` repository state.
2. Current GitHub workflow/run evidence tied to current `main`.
3. Direct live API evidence with timestamps/artifacts.
4. Current official RO App documentation.
5. Older project documents are historical only.

## Completion gates

### Engineering
- [ ] Unit tests GREEN on current HEAD
- [ ] Required production/quality workflows GREEN on current HEAD
- [ ] No known import/runtime failures
- [ ] Canonical structure check PASS
- [ ] Dependency/security review PASS

### RO App API
- [ ] Official API registry complete for required MARSEL entities
- [ ] Every method/path has official evidence
- [x] No guessed endpoints
- [ ] Safe current live GET verification complete
- [ ] Parameterized identifiers never guessed
- [ ] Warehouse/stock contract closed with direct authoritative evidence

### Data
- [ ] Current orders inventory complete
- [ ] Current clients inventory complete
- [ ] Current products inventory complete
- [ ] Current services inventory complete
- [ ] Current warehouses/directories inventory complete
- [ ] Duplicate/anomaly/reference review complete
- [ ] Reconciliation complete

### Recovery
- [ ] Full permitted backup/export created
- [ ] Backup manifest/checksums verified
- [ ] Restore tested safely
- [x] Recovery procedure documented

### Writes
- [ ] Write contracts officially verified
- [ ] Validation complete
- [ ] Dry-run complete
- [ ] Idempotency/duplicate protection complete
- [ ] Rollback procedure tested
- [ ] Post-write verification tested
- [ ] Production writes explicitly enabled only after all gates pass

### MARSEL operations
- [ ] Customer lifecycle defined
- [ ] Repair-to-repeat-sales flow defined
- [ ] Custom manufacturing sales flow defined
- [ ] Daily action queue defined
- [ ] KPI model connected to factual business data
- [ ] Lead attribution and conversion tracking prepared

## Current blockers
1. Backup/export and independent restore/integrity evidence are not proven.
2. Complete current API/entity verification is not proven.
3. Warehouse live contract requires fresh authoritative GET evidence; historical/undocumented compatibility behavior is not promoted to PASS.
4. Duplicate/reference reconciliation requires controlled current evidence; no automatic deletion.
5. Gmail OAuth requires actual user-authorized live verification.
6. Official RO App MCP authorization requires separate live verification.
7. Credential-exposure remediation tracked by Issue #23 requires direct rotation/exposure evidence.
8. GitHub branch protection/ruleset status is not sufficient for production approval: current branch metadata reports `protected=true` but protection enforcement/status checks are `enabled=false` / `off`; account-level security controls remain an open blocker.
9. ReadMe ↔ GitHub bi-directional sync requires external ReadMe configuration in a dedicated docs repository.
10. Current HEAD needs fresh CI verification after the 2026-09-09 security hardening commit.
11. Production WRITE remains disabled until every applicable safety gate passes and explicit authorization exists.

## Issue consolidation — 2026-09-09
Open control issues currently include #19, #23, #27, #30, #77, #83, #85, #91 and #106, plus the newer integration/observability/master-data issues #133, #134 and #135. No issue is marked completed merely because code or documentation exists.

- #19: production gate — BLOCKED / NOT READY.
- #23: credential exposure — SECURITY REMEDIATION REQUIRED.
- #27: Gmail OAuth — IMPLEMENTATION / USER AUTHORIZATION REQUIRED.
- #30: API/entity coverage — REVIEW_REQUIRED.
- #77: published RO App example token — security review/rotation responsibility remains external to this repository.
- #83: evidence discovery — REVIEW_REQUIRED.
- #85: security bridge — BLOCKED until required gates are directly evidenced.
- #91: GitHub account-level controls — MANUAL/EXTERNAL.
- #106: ReadMe GitHub sync — EXTERNAL CONFIGURATION REQUIRED.
- #133: canonical Master Data / Integration Contract — P1, not yet closed.
- #134: observability and correlation contract — P1, not yet closed.
- #135: external integration adapters — P2, READ_ONLY discovery/sandbox verification required before writes.

## Status rule
A gate is `PASS` only when current direct evidence exists. `PLANNED`, `CODED`, `NOT_TESTED`, `ASSUMED`, `OLD_PASS`, or `UNVERIFIED` are not PASS.

## Safety rule
Never claim backup, restore, reconciliation, security rotation, OAuth, MCP authorization or WRITE readiness without direct evidence. Never guess an API endpoint or identifier. Never execute a production mutation merely to make a test green. Never expose or commit `ROAPP_API_KEY`.

## Continuation rule
Every execution starts from this file and the latest verified `main` checkpoint. Verify current evidence, fix the highest-priority safe defect, verify the result, update this checkpoint when repository state changes, and continue. If an external authorization or secret is required and unavailable to connected tools, mark the gate BLOCKED/NOT VERIFIED rather than simulating completion.
