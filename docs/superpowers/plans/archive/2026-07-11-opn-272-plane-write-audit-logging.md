# OPN-272 Plane Write Audit Logging Implementation Plan

> **Archived 2026-07-12:** This completed guardrail slice is no longer the active OPN-272 plan. Linear OPN-272 still needs the ChatGPT/Codex Plane tool surface, auth/permissions, desktop/phone smoke, and setup docs. Keep this file as historical implementation evidence.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add secret-free audit logs for gateway Plane write operations so ChatGPT/Codex create, update, and comment calls have an operator-visible trail.

**Architecture:** Keep the existing gateway Plane write endpoints and SDK calls unchanged. Add structured `INFO` logs around create/update/comment route handlers using route parameters and safe metadata only; do not log request bodies, Plane API keys, bearer tokens, raw upstream payloads, or comment HTML.

**Tech Stack:** FastAPI route handlers, Python logging, existing pytest/httpx ASGI route tests.

---

### Task 1: Route Audit Tests

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py`

- [x] **Step 1: Write failing audit-log test**

Add a test that calls the existing create, update, and comment Plane routes with monkeypatched SDK methods. Assert the `openclaw_gateway.routers.workflow` logger emits one safe audit record for each write operation with:

- `operation` equal to `plane_work_item_create`, `plane_work_item_update`, and `plane_work_item_comment`
- `project_id`
- `work_item_id` for update/comment
- `plane_item_id` for the created/updated/commented response where available
- no API key, gateway bearer token, request body, or comment HTML in the log message

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_workflow_routes.py::test_plane_write_routes_emit_secret_free_audit_logs -q
```

Expected: fail because the route handlers do not emit the new audit records yet.

### Task 2: Audit Implementation

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py`

- [x] **Step 1: Add audit helper**

Add a private helper that logs a stable message such as `plane workflow write audit` with `extra` metadata. Keep the helper local to the workflow router module.

- [x] **Step 2: Log create/update/comment success**

In the create, update, and comment handlers, store the SDK response in a local variable, call the audit helper with safe route metadata and response ID, then return the response.

### Task 3: Verification, Commit, Linear

**Files:**
- Modify: `docs/superpowers/plans/2026-07-11-opn-272-plane-write-audit-logging.md`

- [x] **Step 1: Verify**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_workflow_routes.py tests/test_plane_client.py tests/test_n8n_client.py -q
docker compose -f apps/openclaw-gateway/compose.yml --env-file apps/openclaw-gateway/example.env config --quiet
git diff --check
```

Expected: all commands exit 0.

- [x] **Step 2: Commit and update Linear**

Commit with:

```bash
git commit -m "OPN-272: audit Plane gateway writes"
```

Update OPN-272 and OPN-264 with commit hash, verification, and remaining live ChatGPT/Codex integration gaps.
