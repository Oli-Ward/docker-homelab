# OPN-275 Harden Plane Gateway REST Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the OpenClaw gateway Plane REST facade so SDK errors become stable, secret-free HTTP responses with correlation IDs, and Plane writes emit matching audit metadata.

**Architecture:** Keep Plane API behavior inside `openclaw-plane-sdk`; the gateway owns only FastAPI request handling, response shaping, and audit logging. Add gateway-local error response helpers in `openclaw_gateway.routers.workflow`, pass the incoming `Request` into Plane route wrappers for correlation IDs, and update docs/tests around the retained REST facade.

**Tech Stack:** Python 3.14 local venv, FastAPI, httpx, Pydantic, pytest, pytest-asyncio, `openclaw-plane-sdk`.

## Global Constraints

- Do not run `docker compose up`, `docker compose down`, `docker compose pull`, restart containers, or otherwise mutate live Docker state.
- Do not read or print real `.env` values, API keys, bearer tokens, private keys, session files, runtime state, or logs containing secrets.
- Keep Plane HTTP client behavior in `openclaw-plane-sdk`; do not add direct Plane `httpx` calls to gateway routes.
- Keep current `/v1/workflow/plane/*` paths and methods stable.
- Live write smoke may only be documented as a post-deploy checklist unless the user explicitly approves live writes.

---

## File Structure

- Modify `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py` to add structured Plane error mapping, request correlation IDs, and correlation-aware write audit logging.
- Modify `apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py` to cover the new error body, Plane status-code matrix, timeout/network failures, correlation headers, audit correlation IDs, and compatibility re-exports.
- Modify `apps/openclaw-gateway/README.md` to document the retained REST facade, structured error response shape, auth boundary, read/write distinction, and smoke/deployment checklist.

### Task 1: Structured Plane Error Contract

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py`
- Test: `apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py`

**Interfaces:**
- Consumes: `PlaneApiError.status_code`, `PlaneApiError.kind`, `PlaneResponseError`, `httpx.TimeoutException`, `httpx.HTTPError`.
- Produces: JSON error detail shaped as `{"error_code": str, "message": str, "correlation_id": str, "retryable": bool}`.

- [ ] **Step 1: Write failing structured error tests**

Replace the existing flat Plane error tests with:

```python
@pytest.mark.asyncio
async def test_plane_routes_map_invalid_plane_response_to_structured_gateway_error(monkeypatch):
    async def list_projects(self) -> PlaneProjectsResponse:
        raise PlaneResponseError("plane returned invalid json response with plane-secret")

    monkeypatch.setattr("openclaw_gateway.routers.workflow.PlaneClient.list_projects", list_projects)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/workflow/plane/projects",
            headers={
                "Authorization": "Bearer gateway-secret",
                "X-Request-ID": "request-275",
            },
        )

    assert response.status_code == 502
    assert response.json() == {
        "detail": {
            "error_code": "plane_invalid_response",
            "message": "Plane returned an invalid response.",
            "correlation_id": "request-275",
            "retryable": True,
        }
    }
    assert "plane-secret" not in json.dumps(response.json())
```

Add a parametrized `PlaneApiError` matrix covering 401, 403, 404, 409, 422, 429, and 500.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
../../../.venv/bin/python -m pytest tests/test_workflow_routes.py -q -k "structured_gateway_error or plane_api_errors"
```

Expected: FAIL because `_map_plane_errors` still returns flat string `detail` responses and does not read `X-Request-ID`.

- [ ] **Step 3: Implement the gateway error response helper**

Add `_request_correlation_id(request: Request) -> str`, `_plane_error(...) -> HTTPException`, and change `_map_plane_errors(request, request_callable)` to use this mapping:

- `PlaneResponseError` -> `502`, `plane_invalid_response`, retryable `True`.
- `PlaneApiError(401)` -> `502`, `plane_auth_failed`, retryable `False`, because the upstream Plane credential failed, not the caller bearer token.
- `PlaneApiError(403)` -> `403`, `plane_permission_denied`, retryable `False`.
- `PlaneApiError(404)` -> `404`, `plane_resource_not_found`, retryable `False`.
- `PlaneApiError(409)` -> `409`, `plane_conflict`, retryable `False`.
- `PlaneApiError(422)` -> `422`, `plane_validation_failed`, retryable `False`.
- `PlaneApiError(429)` -> `429`, `plane_rate_limited`, retryable `True`.
- `PlaneApiError(>=500)` -> `502`, `plane_upstream_error`, retryable `True`.
- `httpx.TimeoutException` -> `504`, `plane_timeout`, retryable `True`.
- other `httpx.HTTPError` -> `502`, `plane_request_failed`, retryable `True`.

- [ ] **Step 4: Thread `Request` through all retained Plane REST routes**

Add `request: Request` to read/write Plane route signatures and call `_map_plane_errors(request, ...)`.

- [ ] **Step 5: Run focused error tests**

Run:

```bash
../../../.venv/bin/python -m pytest tests/test_workflow_routes.py -q -k "structured_gateway_error or plane_api_errors"
```

Expected: PASS.

### Task 2: Write Audit Correlation IDs

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py`
- Test: `apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py`

**Interfaces:**
- Consumes: `_request_correlation_id(request)`.
- Produces: write audit log records with `correlation_id` while continuing to omit request bodies and secrets.

- [ ] **Step 1: Update the failing audit test**

In `test_plane_write_routes_emit_secret_free_audit_logs`, send `X-Request-ID: request-275-write` on all three write calls and include `"correlation_id": "request-275-write"` in each expected audit record.

- [ ] **Step 2: Run the audit test to verify it fails**

Run:

```bash
../../../.venv/bin/python -m pytest tests/test_workflow_routes.py -q -k "secret_free_audit_logs"
```

Expected: FAIL because log records do not include `correlation_id`.

- [ ] **Step 3: Add correlation ID to `_audit_plane_write`**

Change `_audit_plane_write` to accept `correlation_id: str` and include it in `extra`. Pass `_request_correlation_id(request)` from create/update/comment routes.

- [ ] **Step 4: Run the audit test**

Run:

```bash
../../../.venv/bin/python -m pytest tests/test_workflow_routes.py -q -k "secret_free_audit_logs"
```

Expected: PASS.

### Task 3: Compatibility and Static SDK Delegation Checks

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py`

**Interfaces:**
- Consumes: `openclaw_gateway.clients.plane`, `openclaw_gateway.schemas.workflow`, `openclaw_plane_sdk`.
- Produces: tests proving transitional imports are compatibility shims and gateway routes do not perform direct Plane HTTP calls.

- [ ] **Step 1: Add compatibility re-export test**

Add a test asserting `openclaw_gateway.clients.plane.PlaneClient is openclaw_plane_sdk.PlaneClient` and `openclaw_gateway.schemas.workflow.PlaneWorkItem is openclaw_plane_sdk.models.PlaneWorkItem`.

- [ ] **Step 2: Add static no-direct-Plane-http test**

Add a test that reads `openclaw_gateway/routers/workflow.py` with `Path` and asserts it does not contain `httpx.AsyncClient` or `X-API-Key`.

- [ ] **Step 3: Run the compatibility/static tests**

Run:

```bash
../../../.venv/bin/python -m pytest tests/test_workflow_routes.py -q -k "compatibility_re_exports or delegates_plane_http"
```

Expected: PASS.

### Task 4: Gateway Documentation

**Files:**
- Modify: `apps/openclaw-gateway/README.md`

**Interfaces:**
- Consumes: implemented route behavior and issue policy.
- Produces: durable documentation of caller auth, read/write routes, error shape, audit correlation, smoke/deploy checklist, and rollback.

- [ ] **Step 1: Update the Plane REST facade section**

Document read routes, write routes, bearer-token auth, gateway-owned Plane credentials, and write audit fields.

- [ ] **Step 2: Document structured error responses**

Add an example `detail` object and list the stable error codes.

- [ ] **Step 3: Document verification and deployment boundary**

Add a checklist for local pytest/static verification and post-Komodo live read/write smoke, image SDK install verification, and rollback confirmation.

### Task 5: Full Local Verification

**Files:**
- No code changes unless verification exposes a defect.

**Interfaces:**
- Consumes: all previous tasks.
- Produces: evidence for final Linear update.

- [ ] **Step 1: Run the full gateway workflow route suite**

Run:

```bash
../../../.venv/bin/python -m pytest tests/test_workflow_routes.py -q
```

Expected: PASS.

- [ ] **Step 2: Run the SDK suite**

Run from `packages/openclaw-plane-sdk`:

```bash
../../.venv/bin/python -m pytest tests -q
```

Expected: PASS.

- [ ] **Step 3: Run static grep checks**

Run from repo root:

```bash
rg -n "httpx.AsyncClient|X-API-Key" apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py
```

Expected: no matches.

Run:

```bash
rg -n "openclaw_gateway\\.clients\\.plane|openclaw_gateway\\.schemas\\.workflow" apps packages docs -g '!**/.venv/**'
```

Expected: only compatibility shim, test, and historical docs/plan references; no new production consumer should be added.

- [ ] **Step 4: Capture git status**

Run:

```bash
git status --short
```

Expected: only the plan, gateway route, gateway tests, and README are modified.

## Self-Review

- Spec coverage: Covers primary OPN-275 gap, audit correlation extension, SDK delegation proof, compatibility re-export decision, docs, and non-mutating verification.
- Placeholder scan: No `TBD`, `TODO`, or unresolved implementation steps.
- Type consistency: `correlation_id` is consistently a `str`; structured error response fields match the issue contract.
