# OPN-270 Plane SDK Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the existing gateway-local Plane API client and Plane models into a reusable `openclaw_plane_sdk` package inside the gateway project, while preserving the gateway's current routes and response contracts.

**Architecture:** Keep the first SDK slice intentionally local and boring: `openclaw_plane_sdk` owns Plane API models, auth header creation, request paths, response normalization, and stable error classes. `openclaw_gateway` imports that package and keeps `openclaw_gateway.schemas.workflow` as a compatibility layer for FastAPI response schemas and existing tests. No live Plane calls or Docker mutations are required.

**Tech Stack:** Python 3.12+, httpx, pydantic, pytest, respx, FastAPI gateway.

---

### Task 1: SDK Package Contract

**Files:**
- Add: `apps/openclaw-gateway/openclaw-gateway/openclaw_plane_sdk/__init__.py`
- Add: `apps/openclaw-gateway/openclaw-gateway/openclaw_plane_sdk/models.py`
- Add: `apps/openclaw-gateway/openclaw-gateway/openclaw_plane_sdk/client.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_plane_client.py`

- [x] **Step 1: Write failing import tests**

Update `tests/test_plane_client.py` to import `PlaneClient`, `PlaneApiError`, `PlaneResponseError`, `PlaneWorkItemCreate`, `PlaneWorkItemUpdate`, and `PlaneCommentCreate` from `openclaw_plane_sdk`.

Run:

```bash
pytest tests/test_plane_client.py -q
```

Expected: fail with `ModuleNotFoundError: No module named 'openclaw_plane_sdk'`.

- [x] **Step 2: Add SDK files**

Move the Plane client implementation to `openclaw_plane_sdk/client.py` and the reusable models to `openclaw_plane_sdk/models.py`. Export the public SDK surface from `openclaw_plane_sdk/__init__.py`.

### Task 2: Gateway Compatibility

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/plane.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/workflow.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py`
- Modify: `apps/openclaw-gateway/README.md`

- [x] **Step 1: Re-export gateway compatibility symbols**

Keep `openclaw_gateway.clients.plane` as a thin re-export so existing imports continue to work during migration.

- [x] **Step 2: Re-export workflow schema models**

Import the reusable Plane models from `openclaw_plane_sdk.models` in `openclaw_gateway.schemas.workflow`, leaving webhook-only schemas in the gateway package.

- [x] **Step 3: Update gateway router imports**

Import `PlaneClient`, `PlaneApiError`, and `PlaneResponseError` directly from `openclaw_plane_sdk`, proving the gateway consumes the SDK.

- [x] **Step 4: Document SDK usage**

Update the gateway README to describe `openclaw_plane_sdk` as the shared Plane API surface for gateway, future MCP tools, CLI helpers, and n8n/OpenClaw helpers.

### Task 3: Verification and Linear

**Files:**
- Modify: this plan file as checkboxes complete.

- [x] **Step 1: Run focused and full verification**

Run:

```bash
pytest tests/test_plane_client.py tests/test_workflow_routes.py tests/test_settings.py -q
pytest -q
docker compose -f apps/openclaw-gateway/compose.yml --env-file apps/openclaw-gateway/example.env config --quiet
git diff --check
```

Expected: all commands exit 0.

- [x] **Step 2: Commit and update Linear**

Commit with:

```bash
git commit -m "OPN-270: extract Plane SDK package"
```

Update OPN-270 and OPN-264 with commit hash, verification, what remains, and any live-smoke caveats.
