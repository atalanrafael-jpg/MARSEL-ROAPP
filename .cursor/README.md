# MARSEL ROAPP — Cursor

Cursor is an execution surface for the single canonical MARSEL ROAPP system. It is not a second source of truth.

## Canonical contract

- GitHub repository: `atalanrafael-jpg/MARSEL ROAPP
- Canonical branch: `main
- Cursor work: temporary agent branch -> review -> PR -> `main
- Live RO App default: READ-ONLY
- Production WRITE: disabled unless the existing production gate explicitly authorizes it with current evidence.

## Cursor account setup

Account-level setup cannot be verified or changed from this repository:

1. Connect GitHub in Cursor Integrations.
2. Grant Cursor access to `atalanrafael-jpg/MARSEL ROAPP.
3. Open Cursor Cloud Agents and select this repository.
4. Confirm the repository environment uses `.cursor/environment.json.
5. Configure any required MCP server in Cursor's MCP settings.
6. Add secrets only through Cursor's secret management; never commit credentials.

## Verification rule

The GitHub repository can verify repository-side configuration. It cannot prove that the Cursor account has authenticated GitHub access, active Cloud Agent access, configured MCP, secrets, or successful agent runs.

Those account-level items remain UNVERIFIED until a direct Cursor run provides evidence.

## Required agent behavior

Every agent must:

- read the current `main state before editing;
- follow `.cursor/rules/MARSEL ROAPP.mdc;
- keep production RO App operations read-only;
- never expose or commit secrets;
- run relevant tests/checks;
- return the changed commit/PR and verification evidence;
- never treat a temporary branch as canonical.

## MCP

MARSEL ROAPP contains its own MCP implementation and setup documentation. Cursor MCP configuration is an execution-layer concern and must use the repository's documented contracts. Live authorization must be directly verified before it is reported as active.

## Source of truth

GitHub `main remains authoritative. Cursor is an agent/execution surface only.
