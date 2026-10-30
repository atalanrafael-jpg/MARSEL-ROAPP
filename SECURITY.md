# Security Policy — MARSEL ROAPP

MARSEL ROAPP is the canonical project for the unified MARSEL business system. Security controls apply to business logic, ROAPP API/integrations, AI/MCP, CI/CD and deployment configuration.

## Mandatory rules

- Never commit API keys, OAuth tokens, refresh tokens, client secrets, passwords, private keys, cookies, or other credentials.
- Production credentials MUST live in protected secret storage (for example GitHub Actions Secrets/Environments or an external secret manager), never in source files, README files, issues, PRs, screenshots, or artifacts.
- `.env` and `.env.*` files are ignored by Git; only `.env.example` may be committed.
- Production WRITE operations remain disabled until the unified production safety gate has direct evidence that they are safe.
- Default live verification mode is READ-ONLY.
- Never claim backup, restore, reconciliation, OAuth, MCP authorization, or WRITE readiness without direct evidence.

## Credential exposure response

Treat every exposed credential as compromised immediately.

1. Revoke or rotate it at the provider.
2. Identify every repository, workflow, log, artifact and deployment that used it.
3. Remove the exposed value from the current tree.
4. If the value exists in Git history, perform an approved history rewrite and verify the old value is no longer reachable from active refs.
5. Store the replacement only in protected secret storage.
6. Re-run security and production-readiness checks.

Deleting a file from `main` does NOT revoke a credential and does NOT remove it from Git history.

## Canonical project

The canonical repository is `atalanrafael-jpg/MARSEL ROAPP and the canonical branch is `main`. Other repositories may provide infrastructure, experiments, upstream sources, or integrations, but they must not silently become a second MARSEL source of truth.

## Verification

Use `.github/workflows/marsel-unified-control-plane.yml` as the canonical audit path. Review repository history, Issues, PRs, Actions runs, logs and artifacts when credential exposure is suspected.
