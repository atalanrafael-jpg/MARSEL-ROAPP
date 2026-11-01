# MARSEL ROAPP Plugin

Read-only RO App inspection and data-quality workflows for Codex, with reusable Skill guidance for ChatGPT.

## What it does

- Fetches bounded RO App order pages.
- Audits orders for duplicate identifiers and missing common fields.
- Reports connector readiness without exposing credentials.
- Never exposes create, update, or delete operations.

## Codex live connector

The plugin bundles a small isolated MCP runtime under `mcp_server/`. It starts with `uv` and reads only these environment variables:

- `ROAPP_API_KEY` — required for live RO App inspection.
- `ROAPP_BASE_URL` — optional; defaults to `https://api.roapp.io/v2`.
- `ROAPP_TIMEOUT_SECONDS` — optional; defaults to `30`.

Install `uv` before using the bundled MCP server. No API key is stored in the plugin.

## ChatGPT

The Skill workflow is portable to ChatGPT. Live RO App access requires a supported connected app/integration; the bundled local stdio MCP server is the Codex execution surface.

## Safety boundary

All exposed RO App operations are read-only. Upstream records are treated as untrusted data, and failures are reported rather than converted into fabricated results.
