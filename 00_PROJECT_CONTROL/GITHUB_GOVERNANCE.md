# MARSEL ROAPP — GitHub Governance

## 1. Canonical source of truth

- Canonical repository: `atalanrafael-jpg/MARSEL-ROAPP`
- Canonical branch: `main`
- MARSEL and ROAPP are one system.
- Other repositories are supporting, upstream, experimental, mirror, or infrastructure repositories and must not become a second MARSEL source of truth.

## 2. Production safety

- Production RO App WRITE remains disabled until explicit evidence gates pass.
- Audit and verification work is GET/read-only by default.
- No credentials, tokens, refresh tokens, API keys, or `.env` files belong in Git.
- A secret exposure is treated as an incident: revoke/rotate first, then clean current content and history.
- No destructive cleanup of branches or historical data is performed solely by age or name.

## 3. Branch model

Use a small controlled branch taxonomy:

- `main` — production/canonical integration branch.
- `feat/<scope>` — feature work.
- `fix/<scope>` — bug/security remediation.
- `chore/<scope>` — repository, documentation, dependency, or governance work.
- `audit/<scope>` — read-only audit/verification work.
- `ci/<scope>` — CI/CD verification work.
- `ops/<scope>` — operational work.
- `backup/<scope>` — temporary recovery references only.
- `dependabot/*` — automated dependency updates.

Do not create version/date branches for routine work unless the branch is an explicit snapshot or recovery point.

## 4. Merge sequence

`issue → branch → implementation → local tests → PR → CI/security/evidence → review → merge → main verification → release/readiness`

A PR is not complete merely because it compiles. Required evidence depends on the change class.

## 5. Change classes

### Code
Require tests, dependency checks, secret scan, and relevant security/quality checks.

### ROAPP integration
Require read-only smoke/audit evidence and explicit API-contract evidence. Never infer undocumented endpoints.

### Data/ERP
Require backup → restore test → reconciliation → dry-run → rollback plan → controlled WRITE approval. Production WRITE is blocked before these gates pass.

### Secrets/security
Revoke/rotate exposed credentials immediately; then clean repository content/history and verify CI/log/artifact exposure.

### AI/MCP/plugins
Require isolated tests, permission boundaries, no implicit production WRITE, and documented connector/runtime requirements.

## 6. Canonical evidence

Every production-relevant change must have a traceable source:

- commit SHA
- PR number
- workflow run
- test/security result
- evidence artifact where applicable
- current-state update for material system changes

## 7. Repository governance

The repository registry is maintained in `00_PROJECT_CONTROL/REPOSITORY_REGISTRY.md`. Supporting repositories must have an explicit role. Unknown repositories are `REVIEW_REQUIRED`, not dependencies by assumption.

## 8. Cleanup rule

Historical branches and files are classified before deletion. Preferred states are `ACTIVE`, `CURRENT`, `SUPERSEDED`, `HISTORICAL`, `EXPERIMENTAL`, `UPSTREAM`, or `REVIEW_REQUIRED`.
