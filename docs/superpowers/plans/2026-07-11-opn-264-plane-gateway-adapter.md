# Plane Gateway Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tested Plane API adapter and protected gateway routes that OpenClaw can reuse for Plane ticket search, read, create, update, comment, and metadata lookup.

**Architecture:** Implement Plane support as a first-class FastAPI gateway module beside the existing media and automation modules. Keep Plane credentials in gateway runtime settings, use `httpx` with `X-API-Key`, map upstream failures to secret-free gateway errors, and expose only narrow authenticated `/v1/workflow/plane` routes.

**Tech Stack:** FastAPI, Pydantic, Pydantic Settings, httpx, pytest, pytest-asyncio, respx, Docker Compose env placeholders.

## Global Constraints

- Do not run `docker compose up`, `docker compose down`, `docker compose pull`, or restart containers directly.
- Do not commit `.env` files, secrets, certificates, private keys, runtime state, database files, logs, or session history.
- Store real Plane credentials outside Git in Komodo or an untracked runtime env file.
- Write tests before production code.
- Plane itself remains private; expose only authenticated gateway operations.

---

### Task 1: Plane Settings And Schemas

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/settings.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/workflow.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_settings.py`

**Interfaces:**
- Produces: `GatewaySettings.plane_api_base_url`, `plane_api_key`, `plane_workspace_slug`, `plane_default_project_id`.
- Produces: Pydantic request/response models consumed by Plane client and routes.

- [ ] **Step 1: Write failing settings tests**
- [ ] **Step 2: Add Plane settings fields**
- [ ] **Step 3: Add workflow schema models**
- [ ] **Step 4: Run settings tests**

### Task 2: Plane Client

**Files:**
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/plane.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_plane_client.py`

**Interfaces:**
- Consumes: Plane base URL, API key, workspace slug, timeout.
- Produces: `PlaneClient` methods for project/list/search/read/create/update/comment operations.

- [ ] **Step 1: Write failing client tests with `respx`**
- [ ] **Step 2: Implement minimal `PlaneClient`**
- [ ] **Step 3: Run client tests**

### Task 3: Plane Workflow Routes

**Files:**
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/main.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py`

**Interfaces:**
- Consumes: `PlaneClient`.
- Produces: protected `/v1/workflow/plane` routes.

- [ ] **Step 1: Write failing route tests**
- [ ] **Step 2: Implement workflow router and include it in app startup**
- [ ] **Step 3: Run route tests**

### Task 4: Compose And Docs

**Files:**
- Modify: `apps/openclaw-gateway/compose.yml`
- Modify: `apps/openclaw-gateway/example.env`
- Modify: `apps/openclaw-gateway/README.md`

**Interfaces:**
- Produces: documented runtime env contract for Plane integration.

- [ ] **Step 1: Add safe env placeholders**
- [ ] **Step 2: Document endpoints and token handling**
- [ ] **Step 3: Validate no real secrets were added**

### Task 5: Verification And Linear Update

**Files:**
- Check: gateway tests.
- Update: Linear `OPN-264`.

**Interfaces:**
- Produces: verification evidence and remaining follow-up list.

- [ ] **Step 1: Run focused Plane tests**
- [ ] **Step 2: Run full gateway tests**
- [ ] **Step 3: Check git diff/status**
- [ ] **Step 4: Add Linear progress comment**
