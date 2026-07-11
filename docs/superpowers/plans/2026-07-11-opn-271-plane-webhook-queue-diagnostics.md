# OPN-271 Plane Webhook Queue Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add read-only diagnostics for the Plane webhook ingress queue so operators can verify queue/dedupe state without reading appdata files directly.

**Architecture:** Keep queue persistence in `openclaw_gateway/plane_webhooks.py` and expose diagnostics through the existing authenticated workflow router. The unauthenticated Plane webhook delivery endpoint stays limited to signed Plane deliveries; humans and smoke scripts use bearer auth for queue status.

**Tech Stack:** FastAPI, Pydantic, pytest/httpx ASGI tests, Docker Compose config validation.

---

### Task 1: Queue Status Endpoint

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/plane_webhooks.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/workflow.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py`

- [x] **Step 1: Write the failing route tests**

Add tests showing:

```python
async def test_plane_webhook_queue_status_requires_auth(tmp_path):
    response = await client.get("/v1/workflow/plane/webhook/queue")
    assert response.status_code == 401
```

and:

```python
async def test_plane_webhook_queue_status_reports_counts(tmp_path):
    # POST two distinct signed deliveries and one duplicate.
    response = await client.get(
        "/v1/workflow/plane/webhook/queue",
        headers={"Authorization": "Bearer gateway-secret"},
    )
    assert response.json()["queued_count"] == 2
    assert response.json()["dedupe_count"] == 2
    assert response.json()["last_delivery_id"] == "delivery-2"
    assert response.json()["last_correlation_id"] == "plane:delivery-2"
```

- [x] **Step 2: Run the focused tests and verify failure**

Run:

```bash
pytest tests/test_workflow_routes.py -q
```

Expected: the new queue status tests fail because the endpoint and schema do not exist yet.

- [x] **Step 3: Implement read-only queue stats**

Add a queue status model and `FilePlaneWebhookQueue.status()` that reads the JSONL queue and dedupe sidecar without mutating them. It should return zero counts when files are absent and never include raw Plane payloads or secrets.

- [x] **Step 4: Wire the authenticated route**

Add `GET /v1/workflow/plane/webhook/queue` to `build_workflow_router(settings)` so it inherits the gateway bearer-token dependency.

- [x] **Step 5: Verify the focused tests pass**

Run:

```bash
pytest tests/test_workflow_routes.py -q
```

Expected: all workflow route tests pass.

### Task 2: Operator Docs And Verification

**Files:**
- Modify: `apps/openclaw-gateway/README.md`
- Optionally modify: `scripts/smoke-openclaw-gateway.sh`
- Optionally modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_smoke_script.py`

- [x] **Step 1: Document the queue diagnostics endpoint**

Update the OpenClaw Gateway README with the authenticated endpoint, response shape, and note that it is read-only diagnostics for queued ingress records.

- [x] **Step 2: Add an opt-in smoke-script check only if it matches existing script style**

If the smoke script has a clean opt-in pattern, add `CHECK_PLANE_WEBHOOK_QUEUE=1` to call the authenticated queue-status endpoint. If not, leave this to a follow-up rather than forcing script churn.

- [x] **Step 3: Run verification**

Run:

```bash
pytest -q
docker compose -f apps/openclaw-gateway/compose.yml --env-file apps/openclaw-gateway/example.env config --quiet
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 4: Commit and update Linear**

Commit with:

```bash
git commit -m "OPN-271: add Plane webhook queue diagnostics"
```

Add Linear comments to OPN-271 and OPN-264 with commit hash, verification, and remaining gaps.
