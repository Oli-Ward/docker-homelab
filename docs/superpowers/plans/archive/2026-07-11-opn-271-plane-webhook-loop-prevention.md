> **Archived/stale plan:** This OPN-271 slice plan is preserved for historical context only. Do not implement from this file directly. Use `docs/superpowers/plans/2026-07-12-opn-271-plane-webhook-desired-state.md` as the current implementation plan for OPN-271.

# OPN-271 Plane Webhook Loop Prevention Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Suppress Plane webhook deliveries created by known automation actors before they enter the OpenClaw webhook queue.

**Architecture:** Keep the public webhook endpoint signed-only, then normalize actor identity from the signed Plane payload. Compare the actor ID against a comma-separated gateway setting, acknowledge suppressed deliveries with a non-queued response, and log enough context for audit without persisting raw payloads.

**Tech Stack:** FastAPI, Pydantic Settings, pytest/httpx ASGI tests, Docker Compose config validation.

---

### Task 1: Suppress Ignored Plane Actors

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/settings.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/workflow.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_settings.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py`

- [x] **Step 1: Write the failing route test**

Add a test that configures `plane_webhook_ignored_actor_ids="automation-user-1,codex-user-1"` and posts a signed event containing:

```python
{
    "event": "issue",
    "action": "update",
    "webhook_id": "webhook-1",
    "actor": {"id": "automation-user-1", "display_name": "OpenClaw Bot"},
    "data": {"id": "work-item-1"},
}
```

Expected response:

```python
{
    "accepted": True,
    "correlation_id": "plane:delivery-1",
    "delivery_id": "delivery-1",
    "event": "issue",
    "action": "update",
    "resource_id": "work-item-1",
    "webhook_id": "webhook-1",
    "actor_id": "automation-user-1",
    "queued": False,
    "duplicate": False,
    "suppressed": True,
    "suppressed_reason": "ignored_actor",
}
```

Also assert the queue file is not created and a `plane webhook suppressed` log record includes `correlation_id`, `plane_actor_id`, and `suppressed_reason`.

- [x] **Step 2: Run the focused tests and verify failure**

Run:

```bash
pytest tests/test_workflow_routes.py -q
```

Expected: the new test fails because actor extraction, suppression, and response fields do not exist yet.

- [x] **Step 3: Implement ignored actor settings and normalization**

Add `plane_webhook_ignored_actor_ids: str = ""` to settings and a method that returns a trimmed set of actor IDs. In the webhook route, extract actor IDs from `actor.id`, `created_by.id`, `updated_by.id`, or `owned_by.id` when present.

- [x] **Step 4: Suppress matching actors before queue append**

If the extracted actor ID is in the ignored set, return `queued: false`, `duplicate: false`, `suppressed: true`, and `suppressed_reason: "ignored_actor"` without calling `FilePlaneWebhookQueue.enqueue()`.

- [x] **Step 5: Verify focused tests pass**

Run:

```bash
pytest tests/test_workflow_routes.py -q
```

Expected: all workflow route tests pass.

### Task 2: Operator Configuration And Verification

**Files:**
- Modify: `apps/openclaw-gateway/compose.yml`
- Modify: `apps/openclaw-gateway/example.env`
- Modify: `apps/openclaw-gateway/README.md`
- Modify: `docs/workflow/plane.md`

- [x] **Step 1: Document the env variable**

Add `PLANE_WEBHOOK_IGNORED_ACTOR_IDS=` to Compose and example env. Document that it should contain Plane user IDs for the gateway service account, OpenClaw write-back user, Codex/ChatGPT integration users, or n8n automation users.

- [x] **Step 2: Document suppression behavior**

Update the gateway README and Plane workflow contract so operators know suppressed deliveries are acknowledged but not queued.

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
git commit -m "OPN-271: suppress Plane automation webhook loops"
```

Add Linear comments to OPN-271 and OPN-264 with commit hash, verification, and remaining gaps.
