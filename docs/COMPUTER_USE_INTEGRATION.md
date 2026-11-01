# MARSEL ROAPP — OpenAI Computer Use

## Implementation status

The API-side Responses loop is implemented in `app/computer_use.py` and exposed at
`POST /api/v1/computer-use/run`. The AI Copilot UI exposes the action to owners and
admins only. It is disabled by default.

**The isolated execution service is a separate deployment requirement.** This repository
does not place generated code inside the FastAPI process. The service URL must point to
a trusted runtime that creates one disposable container/VM per `session_id`, preserves
its Playwright browser and Python namespace between calls, and enforces the supplied
policy. Until that service is deployed and tested, leave `COMPUTER_USE_ENABLED=false`.

## Environment configuration

Set these variables only in the server's secret/environment configuration:

| Variable | Purpose | Default |
|---|---|---|
| `OPENAI_COMPUTER_USE_MODEL` | Model that supports Responses function calling | `gpt-6-astra` |
| `COMPUTER_USE_ENABLED` | Explicit feature gate | `false` |
| `COMPUTER_USE_RUNTIME_URL` | HTTPS execution-service endpoint | empty |
| `COMPUTER_USE_RUNTIME_TOKEN` | Bearer token for the execution service | empty |
| `COMPUTER_USE_ALLOWED_ORIGINS` | JSON array of exact allowed origins | empty |
| `COMPUTER_USE_RUNTIME_TIMEOUT_SECONDS` | Executor request timeout | `45` |
| `COMPUTER_USE_MAX_TURNS` | Maximum Responses iterations | `8` |
| `COMPUTER_USE_MAX_TOOL_CALLS` | Total function executions per task | `12` |
| `COMPUTER_USE_MAX_CODE_CHARS` | Per-script limit | `20000` |
| `COMPUTER_USE_MAX_OUTPUT_IMAGES` | Maximum screenshots per tool call and task | `4` |

Local-development example only:

```dotenv
OPENAI_COMPUTER_USE_MODEL=gpt-6-astra
COMPUTER_USE_ENABLED=true
COMPUTER_USE_RUNTIME_URL=http://127.0.0.1:8765/execute
COMPUTER_USE_RUNTIME_TOKEN=<a-long-random-runtime-token>
COMPUTER_USE_ALLOWED_ORIGINS=["http://127.0.0.1:8000"]
```

Non-local runtime endpoints and allowed origins must use HTTPS. Do not put tokens in
frontend variables, Git, issues, workflow logs, or screenshots.

## Runtime HTTP contract

The API sends one JSON request per generated script:

```json
{
  "session_id": "opaque-random-session-id",
  "language": "python",
  "code": "await page.goto('http://127.0.0.1:8000/app')",
  "policy": {
    "allowed_origins": ["http://127.0.0.1:8000"],
    "network_egress": "allowlist_only",
    "filesystem_access": "disabled",
    "host_environment": "not_inherited",
    "production_write": false,
    "require_approval_for_consequential_actions": true
  }
}
```

Required response shape:

```json
{
  "policy_enforced": true,
  "output": [
    { "type": "input_text", "text": "Page title: MARSEL ROAPP — Control Center" },
    {
      "type": "input_image",
      "image_url": "data:image/png;base64,<base64-bytes>",
      "detail": "original"
    }
  ]
}
```

Only `input_text` and inline PNG/JPEG `input_image` observations are accepted.
The runtime must return actual screenshots as data URLs; screenshot URLs are not fetched
by the API. `policy_enforced: true` is a required runtime contract field, not proof by
itself that an untrusted executor is safe. Use only a runtime you control and have
audited.

## Required isolation properties

The execution service must enforce all of the following outside the generated code:

- One disposable, least-privilege container or VM per session; keep that same environment
  alive for the session's tool loop, then expire it automatically.
- Persistent Playwright `browser`, `context`, `page`, and Python namespace scoped to
  that session only.
- No mount of the application source, host filesystem, Docker socket, credentials,
  application environment variables, or other users' data.
- Non-root user, no Linux capabilities, no privileged mode, CPU/memory/PID/time limits,
  read-only root filesystem, bounded temporary storage, and automatic cleanup.
- Network egress blocked by default and enforced at the container/network boundary;
  permit only the exact configured origins. Re-check redirects, DNS/IP resolution,
  subresources, WebSockets, downloads, and alternate network paths. Do not rely only on
  Playwright navigation checks.
- No direct access to cloud metadata services, private networks, localhost services,
  or RO App APIs unless a specific origin is deliberately allowlisted for a test.
- Stop before consequential actions and return a user-approval request. Model instructions
  alone are not an enforcement boundary.
- Keep screenshots and page content out of logs. Never pass OpenAI or RO App secrets to
  the browser container.

Do not run generated Python in the FastAPI process, and do not treat Python restricted
builtins or Node.js `vm` as a security boundary.

## Tool loop

The service uses a stable `session_id` for every `exec_py` call in one task and
`previous_response_id` for every subsequent Responses API call. Tool outputs preserve
the original `call_id`. The loop is bounded to eight Responses by default and returns
final text plus screenshots to the authenticated application UI.

The API endpoint requires a Supabase-authenticated `owner` or `admin`. Employee access
is denied. Production RO App writes remain disabled.

## Local smoke task

After the isolated execution service is configured and audited, start the FastAPI app
locally and set the local allowlist above. Sign in as an owner/admin and run this task in
AI Copilot → Computer Use:

> Open http://127.0.0.1:8000/app. Read the document title and the visible page heading.
> Take a screenshot. Do not sign in, submit forms, or change any data.

Verify all of the following:

1. The API returns HTTP 200.
2. The final text reports the actual page title and heading.
3. At least one screenshot is returned and is displayed in AI Copilot.
4. The runtime reports policy enforcement and all navigation stayed within the allowlist.
5. A second `exec_py` call in the same task can read the existing `page` without creating
   a new browser session.
6. An unauthenticated/employee request is rejected.
7. With the feature gate off or runtime missing, the endpoint returns 503 and makes no
   OpenAI or runtime request.

## Current verification boundary

Unit tests cover the Responses loop, session continuity, response chaining, bounded turns,
origin allowlist, runtime policy acknowledgement, and screenshot validation. A live local
browser test cannot pass until the external isolated runtime is deployed; do not report
Computer Use as production-ready before that test and CI are green.
