# OPN-59 n8n Limited Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the narrow OpenClaw gateway smoke route for self-hosted n8n and document the n8n-side workflow and rollback without exposing raw n8n access.

**Architecture:** Keep n8n behind the existing OpenClaw gateway boundary. Add a dedicated automation router under `/v1/automation/n8n/openclaw-smoke`, a tiny n8n webhook client that posts a fixed payload, and response schemas that expose only success status, workflow name, received state, and a gateway request ID. Keep n8n workflow creation as media-host UI work documented in the gateway README because workflow state lives under `/data/configs/n8n`, not in Git.

**Tech Stack:** FastAPI, httpx, Pydantic settings/schemas, pytest, Docker Compose config validation.

---

## Files

- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/n8n.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/automation.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/automation.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_automation_routes.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_n8n_client.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/main.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/settings.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_settings.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_smoke_script.py`
- Modify: `apps/openclaw-gateway/compose.yml`
- Modify: `apps/openclaw-gateway/example.env`
- Modify: `apps/openclaw-gateway/README.md`
- Modify: `scripts/smoke-openclaw-gateway.sh`

## Task 1: Settings for n8n Webhook

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/settings.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_settings.py`
- Modify: `apps/openclaw-gateway/compose.yml`
- Modify: `apps/openclaw-gateway/example.env`

- [x] **Step 1: Add failing settings tests**

Add assertions that `GatewaySettings` accepts `n8n_webhook_base_url` and rejects an empty `n8n_openclaw_smoke_path`.

- [x] **Step 2: Run the settings tests**

Run: `cd apps/openclaw-gateway/openclaw-gateway && pytest tests/test_settings.py -q`
Expected: FAIL because the settings fields do not exist yet.

- [x] **Step 3: Add settings fields and compose env wiring**

Add:

```python
n8n_webhook_base_url: AnyHttpUrl
n8n_openclaw_smoke_path: Annotated[str, Field(min_length=1, pattern=r"^/webhook/[A-Za-z0-9._~!$&'()*+,;=:@/-]+$")]
```

Add matching environment variables to compose and safe placeholders to `example.env`.

- [x] **Step 4: Verify settings tests pass**

Run: `cd apps/openclaw-gateway/openclaw-gateway && pytest tests/test_settings.py -q`
Expected: PASS.

## Task 2: n8n Client

**Files:**
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/n8n.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/automation.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_n8n_client.py`

- [x] **Step 1: Add failing client tests**

Test that the client posts exactly `{"source": "openclaw", "test": true, "request_id": "<id>"}` to `/webhook/openclaw-smoke` and parses `{ "ok": true, "workflow": "openclaw-smoke", "received": true }`.

- [x] **Step 2: Run the client tests**

Run: `cd apps/openclaw-gateway/openclaw-gateway && pytest tests/test_n8n_client.py -q`
Expected: FAIL because the client and schemas do not exist yet.

- [x] **Step 3: Implement the minimal client and schemas**

Create `N8nClient.openclaw_smoke(request_id: str) -> N8nSmokeResponse` using `httpx.AsyncClient`, `raise_for_status()`, and existing timeout settings.

- [x] **Step 4: Verify client tests pass**

Run: `cd apps/openclaw-gateway/openclaw-gateway && pytest tests/test_n8n_client.py -q`
Expected: PASS.

## Task 3: Automation Gateway Route

**Files:**
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/automation.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_automation_routes.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/main.py`

- [x] **Step 1: Add failing route tests**

Test that `POST /v1/automation/n8n/openclaw-smoke` requires gateway auth, invokes `N8nClient.openclaw_smoke()`, returns the static n8n result plus a request ID, and maps upstream timeout/status/network errors to 504/502 without leaking tokens.

- [x] **Step 2: Run the route tests**

Run: `cd apps/openclaw-gateway/openclaw-gateway && pytest tests/test_automation_routes.py -q`
Expected: FAIL because the route does not exist.

- [x] **Step 3: Implement automation router and include it in the app**

Add `build_automation_router(settings)` with prefix `/v1/automation`, authenticated through the existing gateway token dependency, and include it in `create_app()`.

- [x] **Step 4: Verify route tests pass**

Run: `cd apps/openclaw-gateway/openclaw-gateway && pytest tests/test_automation_routes.py -q`
Expected: PASS.

## Task 4: Smoke Script and Docs

**Files:**
- Modify: `scripts/smoke-openclaw-gateway.sh`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_smoke_script.py`
- Modify: `apps/openclaw-gateway/README.md`

- [x] **Step 1: Add failing smoke script test**

Extend fake curl coverage to require a call to `/v1/automation/n8n/openclaw-smoke` when `CHECK_N8N_SMOKE=1`.

- [x] **Step 2: Run smoke script tests**

Run: `cd apps/openclaw-gateway/openclaw-gateway && pytest tests/test_smoke_script.py -q`
Expected: FAIL because the script does not call the n8n smoke route yet.

- [x] **Step 3: Implement script option and document operations**

Add `CHECK_N8N_SMOKE=1` behavior to the smoke script. Document the n8n workflow, route, live verification command, logging expectations, and rollback in the gateway README.

- [x] **Step 4: Verify smoke script tests pass**

Run: `cd apps/openclaw-gateway/openclaw-gateway && pytest tests/test_smoke_script.py -q`
Expected: PASS.

## Task 5: Final Verification

**Files:**
- All changed files.

- [x] **Step 1: Run gateway tests**

Run: `cd apps/openclaw-gateway/openclaw-gateway && pytest -q`
Expected: PASS.

- [x] **Step 2: Run compose config validation**

Run: `cd apps/openclaw-gateway && docker compose --env-file example.env config >/tmp/openclaw-gateway-compose.yml`
Expected: PASS without deploying or pulling.

- [x] **Step 3: Run shell syntax check**

Run: `bash -n scripts/smoke-openclaw-gateway.sh`
Expected: PASS.

- [x] **Step 4: Record remaining live work**

Do not mark OPN-59 done unless a live n8n workflow exists and a live gateway smoke succeeds. If repo-side verification passes but live workflow verification has not run, leave the issue active or blocked with a precise comment.
