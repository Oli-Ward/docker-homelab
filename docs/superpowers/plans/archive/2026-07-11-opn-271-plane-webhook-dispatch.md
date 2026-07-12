> **Archived/stale plan:** This OPN-271 slice plan is preserved for historical context only. Do not implement from this file directly. Use `docs/superpowers/plans/2026-07-12-opn-271-plane-webhook-desired-state.md` as the current implementation plan for OPN-271.

# OPN-271 Plane Webhook Dispatch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an authenticated gateway dispatch path that forwards queued Plane webhook events to the configured n8n/OpenClaw workflow and leaves failed deliveries pending for retry.

**Architecture:** Keep signed webhook ingress separate from downstream dispatch. The ingress endpoint appends normalized events to the queue. The authenticated dispatch endpoint reads pending queue events, forwards them to one fixed n8n webhook path, and records successfully dispatched delivery IDs in a sidecar file. Failed deliveries are not marked dispatched, so later dispatch calls retry them.

**Tech Stack:** FastAPI, httpx, Pydantic Settings, pytest/httpx ASGI tests, respx, Docker Compose config validation.

---

### Task 1: n8n Plane Dispatch Client

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/n8n.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_n8n_client.py`

- [x] **Step 1: Write the failing client test**

Add a test showing `N8nClient.forward_plane_webhook_event()` posts a normalized Plane event to `/webhook/plane-openclaw-dispatch` with no raw payload fields.

- [x] **Step 2: Run the n8n client tests and verify failure**

Run:

```bash
pytest tests/test_n8n_client.py -q
```

Expected: the new test fails because the method does not exist.

- [x] **Step 3: Implement the client method**

Add `plane_dispatch_path` to the client constructor and implement `forward_plane_webhook_event(event: dict[str, object]) -> dict[str, object]` using the same timeout/error behavior as the existing n8n methods.

### Task 2: Queue Pending/Dispatched State

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/plane_webhooks.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py`

- [x] **Step 1: Write route tests for dispatch success and retry**

Add tests that:

1. Queue two signed Plane events.
2. Call `POST /v1/workflow/plane/webhook/dispatch`.
3. Assert both events are forwarded to n8n and marked dispatched.
4. Assert a second dispatch call sends nothing because no events are pending.

Add a second test where n8n fails for the first event and assert the endpoint returns a gateway error, no delivery is marked dispatched, and a later successful call retries the same event.

- [x] **Step 2: Run workflow tests and verify failure**

Run:

```bash
pytest tests/test_workflow_routes.py -q
```

Expected: dispatch route and queue pending helpers are missing.

- [x] **Step 3: Implement queue helpers**

Add:

- `pending_events(limit: int) -> list[dict[str, object]]`
- `mark_dispatched(delivery_id: str) -> None`
- `dispatched_path` sidecar derived from queue path, unless explicitly configured later.

### Task 3: Authenticated Dispatch Route

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/settings.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/workflow.py`

- [x] **Step 1: Add settings and schema**

Add `n8n_plane_webhook_dispatch_path` with a safe fixed webhook-path validation pattern and a gateway response schema with dispatched count, pending count, delivery IDs, and failed delivery ID.

- [x] **Step 2: Implement route**

Add authenticated:

```text
POST /v1/workflow/plane/webhook/dispatch?limit=10
```

The route should forward pending events in order. If n8n returns timeout, HTTP status error, or network error, return a secret-free gateway error and leave the failed event pending.

- [x] **Step 3: Verify focused tests pass**

Run:

```bash
pytest tests/test_workflow_routes.py tests/test_n8n_client.py -q
```

Expected: all focused dispatch tests pass.

### Task 4: Docs, Env, Verification, Linear

**Files:**
- Modify: `apps/openclaw-gateway/compose.yml`
- Modify: `apps/openclaw-gateway/example.env`
- Modify: `apps/openclaw-gateway/README.md`
- Modify: `docs/workflow/plane.md`

- [x] **Step 1: Document dispatch config and behavior**

Add `N8N_PLANE_WEBHOOK_DISPATCH_PATH=/webhook/plane-openclaw-dispatch` to Compose/example env and document the dispatch endpoint, retry behavior, and remaining need for an actual n8n/OpenClaw workflow.

- [x] **Step 2: Run verification**

Run:

```bash
pytest -q
docker compose -f apps/openclaw-gateway/compose.yml --env-file apps/openclaw-gateway/example.env config --quiet
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 3: Commit and update Linear**

Commit with:

```bash
git commit -m "OPN-271: dispatch Plane webhook queue to n8n"
```

Add Linear comments to OPN-271 and OPN-264 with commit hash, verification, and remaining gaps.
