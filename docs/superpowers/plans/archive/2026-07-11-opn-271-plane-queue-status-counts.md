> **Archived/stale plan:** This OPN-271 slice plan is preserved for historical context only. Do not implement from this file directly. Use `docs/superpowers/plans/2026-07-12-opn-271-plane-webhook-desired-state.md` as the current implementation plan for OPN-271.

# OPN-271 Plane Queue Status Counts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the read-only Plane webhook queue diagnostics endpoint so operators can see total queued, dispatched, and still-pending delivery counts before touching live dispatch.

**Architecture:** Extend `FilePlaneWebhookQueue.status()` to read the existing `.dispatched` sidecar file and compute `dispatched_count` plus `pending_count` from valid queued records whose delivery IDs are not dispatched. Return those fields through the existing authenticated `GET /v1/workflow/plane/webhook/queue` endpoint and document the response shape.

**Tech Stack:** FastAPI route models, Pydantic schemas, file-backed JSONL queue helper, pytest/httpx route tests, Docker Compose config validation.

## Global Constraints

- Do not dispatch, replay, mutate, or delete queue records.
- Do not run Docker deploy/restart/pull/up/down commands.
- Do not read or print real `.env` files or secrets.
- Keep diagnostics authenticated through the existing gateway bearer-token route.
- Treat malformed queue records as malformed, not pending.

---

### Task 1: Queue Status Test Coverage

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py`

**Interfaces:**
- Consumes: `GET /v1/workflow/plane/webhook/queue`
- Produces: failing tests for `pending_count` and `dispatched_count`.

- [x] **Step 1: Update empty queue expectation**

Add `dispatched_count: 0` and `pending_count: 0` to `test_plane_webhook_queue_status_reports_empty_missing_queue`.

- [x] **Step 2: Update populated queue expectation**

In `test_plane_webhook_queue_status_reports_counts`, dispatch one delivery or write a dispatched sidecar entry, then assert:

- `queued_count` still reports total valid queued records
- `dispatched_count` reports dispatched delivery IDs found in the sidecar
- `pending_count` reports valid queued records not marked dispatched

- [x] **Step 3: Run the focused tests and verify red**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway && python -m pytest tests/test_workflow_routes.py::test_plane_webhook_queue_status_reports_empty_missing_queue tests/test_workflow_routes.py::test_plane_webhook_queue_status_reports_counts -q
```

Expected: fail because the response does not include `dispatched_count` or `pending_count`.

### Task 2: Queue Status Implementation

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/plane_webhooks.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/workflow.py`

**Interfaces:**
- Produces: `PlaneWebhookQueueStatus.dispatched_count: int`
- Produces: `PlaneWebhookQueueStatus.pending_count: int`
- Produces: `PlaneWebhookQueueStatusResponse.dispatched_count: int`
- Produces: `PlaneWebhookQueueStatusResponse.pending_count: int`

- [x] **Step 1: Add Pydantic fields**

Add `dispatched_count: int` and `pending_count: int` to both queue status models.

- [x] **Step 2: Compute counts from existing files**

In `FilePlaneWebhookQueue.status()`, read dispatched delivery IDs once, increment `pending_count` only for valid queue records whose `delivery_id` is a string and is not in the dispatched set, and set `dispatched_count` to the sidecar set size.

- [x] **Step 3: Verify focused tests pass**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway && python -m pytest tests/test_workflow_routes.py::test_plane_webhook_queue_status_reports_empty_missing_queue tests/test_workflow_routes.py::test_plane_webhook_queue_status_reports_counts -q
```

Expected: pass.

### Task 3: Docs, Verification, Commit, Linear

**Files:**
- Modify: `apps/openclaw-gateway/README.md`
- Modify: `docs/workflow/plane.md`
- Modify: `docs/superpowers/plans/2026-07-11-opn-271-plane-queue-status-counts.md`

**Interfaces:**
- Produces: documented queue status response fields and final Linear checkpoint.

- [x] **Step 1: Document queue status counts**

Update the Plane webhook queue diagnostics docs to include `dispatched_count` and `pending_count`, explaining that the endpoint is read-only and does not mark events dispatched.

- [x] **Step 2: Run verification**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway && python -m pytest tests/test_workflow_routes.py tests/test_n8n_client.py -q
docker compose -f apps/openclaw-gateway/compose.yml --env-file apps/openclaw-gateway/example.env config --quiet
git diff --check
```

Run a focused changed-file secret scan.

- [ ] **Step 3: Commit and update Linear**

Commit with:

```bash
git commit -m "OPN-271: report Plane queue pending counts"
```

Update OPN-271 and OPN-264 with commit hash, verification, and remaining live gaps.
