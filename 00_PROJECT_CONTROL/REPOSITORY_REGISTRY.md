# MARSEL ROAPP — Repository Registry

Status values: `CANONICAL`, `SUPPORTING`, `UPSTREAM`, `EXPERIMENTAL`, `SECURITY`, `PRIVATE`, `REVIEW_REQUIRED`.

| Repository | Status | Role | Rule |
|---|---|---|---|
| `MARSEL-ROAPP` (`atalanrafael-jpg/MARSEL-ROAPP`) | CANONICAL | MARSEL × ROAPP application, audits, integrations, CI/CD | Single source of truth |
| `ROAPP_API_KEY` | PRIVATE / SECURITY | Historical credential-handling repository | Never store live credentials; migrate to GitHub Secrets/secret manager |
| `New-repository-secret` | SECURITY / REVIEW_REQUIRED | Credential exposure incident repository | Do not use for secrets; investigate history/metadata and rotate exposed credentials |
| `codex` | UPSTREAM / REVIEW_REQUIRED | Codex source or mirror | Not a MARSEL dependency unless explicitly pinned/documented |
| `codex-security` | SUPPORTING / SECURITY | Security tooling | Use for security workflows where applicable |
| `openai-agents-python` | UPSTREAM | OpenAI Agents SDK source | Dependency only through explicit version/pin |
| `openai-agents-js` | UPSTREAM | OpenAI Agents JS source | Dependency only through explicit version/pin |
| `n8n` | SUPPORTING / UPSTREAM | Automation platform source/integration | External automation; no second MARSEL source of truth |
| `servers` | SUPPORTING / REVIEW_REQUIRED | MCP/server infrastructure | Explicitly document each production dependency |
| `plugins` | SUPPORTING / REVIEW_REQUIRED | Plugin ecosystem | Only approved plugins may be used in production |
| `desktopcommandermcp` | SUPPORTING | MCP/desktop automation | Privileged automation; keep outside production data path unless gated |
| `chrome-devtools-mcp` | SUPPORTING | Browser automation | Diagnostic/automation layer only unless separately approved |
| `smartbear-mcp` | SUPPORTING | MCP tooling | Use only for documented test/quality use cases |
| `zapier-mcp` | SUPPORTING | Integration automation | Credentials remain external to Git |
| `archestra` | SUPPORTING / REVIEW_REQUIRED | AI/MCP infrastructure | Dependency status must be explicitly proven |
| `gpt-oss` | UPSTREAM / REVIEW_REQUIRED | AI model source | Not a production dependency by repository presence alone |
| `openai-cli` | SUPPORTING / UPSTREAM | CLI tooling | Version/purpose must be pinned before production use |
| `openai-openapi` | UPSTREAM | OpenAPI specifications | Reference source only |

## Governance rule

This registry is a control document, not proof that every listed repository is currently used. A repository becomes a production dependency only when code, workflow, deployment configuration, or documentation in `MARSEL-ROAPP` establishes that dependency.

## Required next classification

For each non-canonical repository, verify: fork/source relationship, purpose, active dependency references, credentials, Actions, and whether it can be archived. No deletion is authorized by this registry alone.
