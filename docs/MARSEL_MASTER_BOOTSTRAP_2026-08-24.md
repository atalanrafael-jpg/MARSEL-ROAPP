# MARSEL MASTER BOOTSTRAP

Date: 2026-08-24
Status: historical control-point record, superseded by current `01_MASTER/*` documents.

## Purpose

Establish a fresh canonical control point for MARSEL / ROAPP without changing RO App production data.

## Canonical system at historical checkpoint

- Business contour: MARSEL
- Technology contour: ROAPP
- Canonical repository: `atalanrafael-jpg/MARSEL-ROAPP`
- Canonical branch: `main`
- Current canonical branch: `main-MARSEL-ROAPP`
- `main` does not currently exist and is not authoritative.
- Canonical live audit workflow: `.github/workflows/marsel-unified-control-plane.yml`
- Historical implementations are preserved under `06_ARCHIVE/`.

## Historical control facts

- Repository is active, public, not archived.
- `main-MARSEL-ROAPP` is the default/canonical branch.
- The unified system definition explicitly defines MARSEL + ROAPP as one system.
- The canonical control plane is READ-ONLY and blocks production WRITE.
- Production WRITE is disabled until backup/export, restore integrity, reconciliation, full READ-ONLY inventory, duplicate/orphan/reference analysis, dry-run, idempotency, rollback and post-write verification are directly evidenced.

## Canonical governance

All branches, tests, runs, deployments, implementations, improvements, repositories, workflows, integrations, applications and documentation are subordinate to the single MARSEL ROAPP control plane. `main` is the only canonical integration branch; temporary branches are working branches and are not independent sources of truth.

See `docs/MARSEL_ROAPP_CANONICAL_GOVERNANCE.md` for the enforced project-wide rules.

## Current open gates

All branches, tests, runs, deployments, implementations, improvements, repositories, workflows, integrations, applications and documentation are subordinate to the single MARSEL ROAPP control plane. `main-MARSEL-ROAPP` is the canonical integration branch; temporary branches are working branches and are not independent sources of truth.

See `docs/MARSEL_ROAPP_CANONICAL_GOVERNANCE.md` for the enforced project-wide rules.

## Historical open gates retained for traceability

These items were open at the original bootstrap checkpoint and must not be treated as current status without fresh evidence:
1. Fresh live READ-ONLY evidence for the documented warehouse list contract.
2. Complete current API/entity coverage and verified parameterized GET probes.
3. Full backup/export evidence and verified restore/integrity test.
4. Classification of 11 product-code duplicate groups; no automatic deletion/merge.
5. User-authorized Gmail OAuth READ-ONLY verification.
6. Official RO App MCP authorization verification.
7. Security remediation/evidence for the historical credential-exposure issue.

## Safety decision

`PRODUCTION_WRITE = BLOCKED`

No production mutation, mass synchronization, deletion, merge, reconciliation write, or irreversible data operation is authorized by this bootstrap.

## Control rule

Fresh evidence from the current canonical branch must replace historical assumptions. A successful CI run alone is not proof of production synchronization. Missing or incomplete evidence is `REVIEW_REQUIRED`, not `PASS`.

## Status

`HISTORICAL / SUPERSEDED`
