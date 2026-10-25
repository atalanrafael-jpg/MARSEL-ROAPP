# MARSEL ROAPP — Canonical Governance

Date: 2026-09-09
Date: 2026-09-13

## 1. Single system

MARSEL ROAPP is one system:

- Business contour: **Ювелирная студия MARSEL**
- Technology contour: **ROAPP**
- Canonical repository: `atalanrafael-jpg/MARSEL-ROAPP`
- Canonical branch: `main`
- Canonical live audit control plane: `.github/workflows/marsel-unified-control-plane.yml`

No other repository, branch, workflow, application, integration, deployment, test suite, or document may silently become a competing MARSEL ROAPP source of truth.

## 2. Branch policy

`main` is the current canonical integration branch.

All other branches are temporary working branches and must have a documented MARSEL ROAPP purpose. They are not independent project sources.

Branch classes:

- `chore/*`, `fix/*`, `feat/*`, `feature/*`, `docs/*`, `ci/*`, `automation/*`, `audit/*`, `codex/*`, `cloudflare/*`, `erp-*`, `act/*`, `agent/*`, `ai/*`, and security branches: temporary project work only.
- `backup/*`: historical recovery points only; never a source of truth.
- `старые данные/*` is repository historical material, not a live source of truth.

A temporary branch must not be treated as production state until its changes are reviewed and integrated into `main`.

A temporary branch must not be treated as production state until its changes are reviewed and integrated into the canonical branch.

## 3. Workflow policy

GitHub Actions are components of MARSEL ROAPP, not separate projects.

The canonical live RO App audit is exactly one path:

`.github/workflows/marsel-unified-control-plane.yml`

Supporting workflows may test or guard specific responsibilities, but must not create a second live production audit path or claim production readiness independently.

## 4. Test policy

Tests must execute against the MARSEL ROAPP repository and its declared contracts. A generic test workflow must not silently perform a live RO App audit.

External/live evidence is distinct from local CI evidence. CI success alone never proves RO App production synchronization, data correctness, OAuth authorization, MCP authorization, backup/restore integrity, or production WRITE readiness.

## 5. Integration policy

RO App, MCP, ChatGPT/Codex, GitHub, and other connected services are integration components of MARSEL ROAPP when explicitly registered. Credentials are never stored in source, documentation, issues, PRs, logs, or artifacts.

Unverified integrations remain `NOT_VERIFIED` or `BLOCKED`; they must not be represented as completed.

## 6. Production safety

`PRODUCTION_WRITE = DISABLED` remains the default.

No branch, test, deployment, agent, workflow, MCP server, integration, or application may bypass the production gate or independently authorize a production mutation.

Required evidence before controlled production WRITE remains:

`backup/export → restore integrity → schema reconciliation → full READ-ONLY inventory → duplicate/orphan/reference analysis → dry-run → idempotency → rollback → controlled write → post-write verification`

## 7. Consolidation rule

Do not delete or merge branches solely because their names overlap. First inspect their commits, PRs, workflow impact, unique fixes, evidence, and whether their changes are already present in `main`.
Do not delete or merge branches solely because their names overlap. First inspect their commits, PRs, workflow impact, unique fixes, evidence, and whether their changes are already present in the canonical branch.

The consolidation target is:

`many temporary work branches → reviewed changes → main → historical branches retained only when justified`

## 8. Evidence precedence

1. Current `main`.
2. Current CI evidence tied to the relevant commit.
3. Direct live evidence with timestamp/artifact.
4. Current official RO App documentation.
5. Historical branches/documents as context only.

Missing or conflicting evidence is `REVIEW_REQUIRED`, not `PASS`.

## 9. Required invariant

Every project artifact must be traceable to:

`MARSEL ROAPP → repository → branch/commit → task/PR → test/evidence → verification → result`

Anything that cannot be traced through this chain is not an authoritative MARSEL ROAPP result.

main is the only canonical integration branch.
