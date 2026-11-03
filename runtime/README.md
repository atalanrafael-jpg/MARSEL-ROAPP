# MARSEL ROAPP — Isolated Computer Use Runtime

This service is designed to run inside one disposable Vercel Sandbox microVM per Computer Use task. Do not expose it as a shared public service and do not run generated code in the main application process.

## Contract

- `POST /execute` accepts a task session ID, Python code, and an exact origin allowlist.
- The runtime keeps one Playwright browser, context, page, and Python namespace for the life of the session.
- Each execution returns text observations and an original-resolution PNG screenshot as a data URL.
- `DELETE /sessions/{session_id}` closes the browser and releases the session.
- Bearer authentication is mandatory.
- Execution is refused unless the trusted launcher attests that the Vercel Sandbox network policy was successfully applied.
- Runtime requests cannot expand the launcher's origin allowlist.
- Consequential actions and production writes remain disabled by default.

## Isolation requirements

The Vercel Sandbox microVM is the security boundary. The trusted launcher must:

1. Create a disposable sandbox with a custom egress allowlist derived from the exact user-approved origins.
2. Keep application API keys, RO App credentials, Vercel credentials, and host environment variables out of the sandbox.
3. Install Playwright and Chromium before narrowing egress to the approved task origins.
4. Set the network-policy attestation flag only after the Vercel API confirms the restrictive policy.
5. Generate a unique runtime bearer token for this sandbox and pass only that token to the runtime process.
6. Set the runtime origin allowlist to the same origins used by the network policy.
7. Destroy the disposable sandbox after the task, including on timeout or error.

The filesystem policy means sandbox-local filesystem only. The runtime does not mount the host application's filesystem. Do not describe the sandbox's own temporary filesystem as disabled.

## Local smoke test

Install the runtime dependencies and Chromium in an isolated environment:

```bash
python -m pip install -r runtime/requirements.txt
python -m playwright install chromium
```

Use only a non-production token and a local test page when starting a local runtime. Do not set the network-policy attestation flag outside a sandbox whose egress policy has actually been verified.
