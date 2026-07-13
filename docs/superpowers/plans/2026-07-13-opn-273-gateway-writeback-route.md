# OPN-273 Gateway Writeback Route Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `POST /v1/workflow/plane/writeback` to the media gateway so OpenClaw can apply one planned Plane write-back through the in-gateway Plane client.

**Architecture:** Keep the route in `openclaw_gateway.routers.workflow` beside the existing Plane facade writes. Add small Pydantic request/response models in `openclaw_gateway.schemas.workflow`, reuse `_map_plane_errors(...)`, call `PlaneClient.update_work_item(...)` and/or `PlaneClient.add_comment(...)`, then return `{ "ok": true, "applied": true }` only after the selected calls complete.

**Tech Stack:** FastAPI, Pydantic, pytest, httpx ASGI transport, `openclaw-plane-sdk`.

## Global Constraints

- Do not run Docker deployment, restart, pull, or live mutation commands.
- Keep Plane credentials only in gateway runtime settings.
- Do not expose raw Plane payloads, API keys, bearer tokens, comments, or descriptions in logs.
- Preserve existing dirty files outside this slice.
- Validate with focused pytest and non-deploying `docker compose config`.

---

### Task 1: Add Route Test

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py`

**Interfaces:**
- Consumes: existing `make_app(...)`, `PlaneWorkItem`, `PlaneComment`, and monkeypatched `PlaneClient`.
- Produces: failing coverage for `POST /v1/workflow/plane/writeback`.

- [x] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_plane_writeback_route_applies_one_operation(monkeypatch, caplog):
    observed = {}

    async def update_work_item(self, project_id, work_item_id, update):
        observed["update"] = (project_id, work_item_id, update.state_id)
        return PlaneWorkItem(id=work_item_id, name="Updated", project_id=project_id, state_id=update.state_id)

    async def add_comment(self, project_id, work_item_id, comment):
        observed["comment"] = (project_id, work_item_id, comment.comment_html)
        return PlaneComment(id="comment-1", comment_html=comment.comment_html)

    monkeypatch.setattr("openclaw_gateway.routers.workflow.PlaneClient.update_work_item", update_work_item)
    monkeypatch.setattr("openclaw_gateway.routers.workflow.PlaneClient.add_comment", add_comment)

    transport = httpx.ASGITransport(app=make_app())
    headers = {"Authorization": "Bearer gateway-secret", "X-Request-ID": "request-writeback"}
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/workflow/plane/writeback",
            headers=headers,
            json={
                "claim": {"claim_id": "claim-1", "source_identifier": "OPENC-261", "phase": "pr_opened"},
                "operation": {
                    "project_id": "project-1",
                    "work_item_id": "work-item-1",
                    "state_id": "state-review",
                    "comment_html": "<p>PR opened: https://github.example/pr/4</p>",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "applied": True}
    assert observed == {
        "update": ("project-1", "work-item-1", "state-review"),
        "comment": ("project-1", "work-item-1", "<p>PR opened: https://github.example/pr/4</p>"),
    }
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd apps/openclaw-gateway/openclaw-gateway && python -m pytest tests/test_workflow_routes.py::test_plane_writeback_route_applies_one_operation -q`

Expected: `404 Not Found` or import/model failure because the route does not exist yet.

Result: the initial red output was superseded by the final focused route
verification below; this plan now records the completed implementation state.

### Task 2: Add Models And Route

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/workflow.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py`
- Modify: `apps/openclaw-gateway/README.md`

**Interfaces:**
- Produces: `PlaneWritebackRequest`, `PlaneWritebackOperation`, `PlaneWritebackClaim`, `PlaneWritebackResponse`.

- [x] **Step 1: Add schema models**

Add models with required `operation.project_id` and `operation.work_item_id`; optional `state_id`, work-item update fields, and `comment_html`; flexible claim metadata for audit correlation.

- [x] **Step 2: Add route implementation**

Use one `PlaneClient`. If the operation has any update fields, call `update_work_item(...)`. If `comment_html` is present, call `add_comment(...)`. Reject operations with no update/comment action using HTTP 422. Use `_map_plane_errors(...)` around the composed apply function.

- [x] **Step 3: Run focused test**

Run: `cd apps/openclaw-gateway/openclaw-gateway && python -m pytest tests/test_workflow_routes.py::test_plane_writeback_route_applies_one_operation -q`

Expected: pass.

### Task 3: Verify Route Slice

**Files:**
- Validate: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py`
- Validate: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/workflow.py`
- Validate: `apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py`
- Validate: `apps/openclaw-gateway/README.md`

- [x] **Step 1: Run full workflow route tests**

Run: `cd apps/openclaw-gateway/openclaw-gateway && python -m pytest tests/test_workflow_routes.py -q`

Expected: all workflow route tests pass.

- [x] **Step 2: Run SDK tests**

Run: `python -m pytest packages/openclaw-plane-sdk/tests -q`

Expected: SDK tests pass.

- [x] **Step 3: Render compose without deployment**

Run: `docker compose -f apps/openclaw-gateway/compose.yml --env-file apps/openclaw-gateway/example.env config --quiet`

Expected: exit 0.

- [x] **Step 4: Check diff hygiene**

Run: `git diff --check -- apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/workflow.py apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py apps/openclaw-gateway/README.md docs/superpowers/plans/2026-07-13-opn-273-gateway-writeback-route.md`

Expected: no output and exit 0.

## 2026-07-13 Verification

- `PYTHONPATH=.:../../../packages/openclaw-plane-sdk/src python -m pytest tests/test_workflow_routes.py -q` from `apps/openclaw-gateway/openclaw-gateway` -> `35 passed`.
- `PYTHONPATH=src python -m pytest tests/test_plane_client.py -q` from `packages/openclaw-plane-sdk` -> `15 passed`.
- `docker compose -f apps/openclaw-gateway/compose.yml --env-file apps/openclaw-gateway/example.env config --quiet` -> passed.
- `git diff --check` -> passed.
