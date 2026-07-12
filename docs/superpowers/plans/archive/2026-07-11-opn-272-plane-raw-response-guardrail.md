# OPN-272 Plane Raw Response Guardrail Implementation Plan

> **Archived 2026-07-12:** This completed guardrail slice is no longer the active OPN-272 plan. Linear OPN-272 still needs the ChatGPT/Codex Plane tool surface, auth/permissions, desktop/phone smoke, and setup docs. Keep this file as historical implementation evidence.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent gateway Plane API responses from exposing SDK `raw` upstream payload fields to ChatGPT/Codex/OpenClaw callers.

**Architecture:** Keep `raw` on SDK models for internal diagnostics and mapping tests, but exclude `raw` at the FastAPI route boundary for all Plane project/state/label/work-item/comment responses. Use route-level `response_model_exclude` so SDK internals remain unchanged.

**Tech Stack:** FastAPI response models, Pydantic model serialization, existing pytest/httpx ASGI route tests.

---

### Task 1: Raw Payload Boundary Test

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py`

- [x] **Step 1: Write failing route-boundary test**

Add a test that monkeypatches Plane SDK route methods to return models whose `raw` fields contain sentinel values. Call representative Plane read/write routes through the ASGI app and assert:

- response JSON does not contain any `raw` keys
- response JSON does not contain sentinel raw payload values
- normalized fields such as `id`, `name`, and `comment_html` still serialize

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_workflow_routes.py::test_plane_routes_exclude_raw_upstream_payloads -q
```

Expected: fail because the current route responses serialize SDK `raw` fields.

### Task 2: Route Response Exclusions

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py`

- [x] **Step 1: Add response exclusion constants**

Add module-level constants for excluding `raw` from list responses and single-object responses.

- [x] **Step 2: Apply exclusions to Plane routes**

Apply `response_model_exclude` to:

- `GET /plane/projects`
- `GET /plane/projects/{project_id}/states`
- `GET /plane/projects/{project_id}/labels`
- `GET /plane/search`
- `GET /plane/projects/{project_id}/work-items`
- `GET /plane/projects/{project_id}/work-items/{work_item_id}`
- `POST /plane/projects/{project_id}/work-items`
- `PATCH /plane/projects/{project_id}/work-items/{work_item_id}`
- `POST /plane/projects/{project_id}/work-items/{work_item_id}/comments`

### Task 3: Verification, Commit, Linear

**Files:**
- Modify: `apps/openclaw-gateway/README.md`
- Modify: `docs/superpowers/plans/2026-07-11-opn-272-plane-raw-response-guardrail.md`

- [x] **Step 1: Verify**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_workflow_routes.py tests/test_plane_client.py -q
docker compose -f apps/openclaw-gateway/compose.yml --env-file apps/openclaw-gateway/example.env config --quiet
git diff --check
```

Expected: all commands exit 0.

- [x] **Step 2: Commit and update Linear**

Commit with:

```bash
git commit -m "OPN-272: exclude raw Plane gateway responses"
```

Update OPN-272 and OPN-264 with commit hash, verification, and remaining live ChatGPT/Codex integration gaps.
