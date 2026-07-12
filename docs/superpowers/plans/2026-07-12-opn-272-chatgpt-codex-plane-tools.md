# OPN-272 ChatGPT/Codex Plane Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Plane usable from ChatGPT and Codex through the existing gateway-backed Plane routes, with authenticated read/search/list/create/update/comment operations and safe smoke evidence.

**Architecture:** Do not add a separate Plane MCP service for this slice. Add a thin tool adapter inside `openclaw-gateway` that talks to the existing `/v1/workflow/plane/...` REST routes using the gateway bearer token, then publish the same narrow operation contract as a ChatGPT Action OpenAPI document and a local Codex-friendly CLI. Gateway remains the only runtime that holds the Plane API key; ChatGPT/Codex only receive the gateway URL/token.

**Tech Stack:** Python 3.12, FastAPI/httpx/Pydantic, existing `openclaw-gateway` route models, pytest, Docker Compose config validation, ChatGPT Action OpenAPI YAML.

---

## Issue Context

Linear issue: `OPN-272` — `Implement ChatGPT/Codex Plane Integration`

Approved decisions from the issue comments:

- Use existing `openclaw-gateway` as the backend for ChatGPT/Codex Plane tools.
- Do not build a separate Plane MCP/app service in the first slice.
- Use a service token to authenticate tool calls to the gateway; never expose the Plane API key to ChatGPT or Codex.
- Allow read/search/list, create, update, and comment.
- Do not implement delete/archive/destructive or broad bulk update operations.
- New chat-created tickets default to `Todo`; they must not auto-enter `Ready for Agent`.
- Moving to `Ready for Agent` requires explicit confirmation and complete agent-ready checklist evidence.
- Phone support is satisfied by the ChatGPT Action path; no mobile app or shortcut is required.
- Container/gateway logs are sufficient audit retention for the first smoke.

Already completed guardrail slices:

- `f1b2119b2e708bb07384c5a99811de7e0cd2aa2f` added secret-free audit logs for create/update/comment.
- `22b0720beb4663e1f5ef015515d3c9e6f539a291` excluded SDK `raw` upstream payloads from gateway route responses.

Blocking/dependency note:

- Linear still lists `OPN-270` as a blocker. Before implementation, confirm the reusable SDK dependency is actually satisfied in this checkout by checking that `apps/openclaw-gateway/openclaw-gateway/pyproject.toml` has the editable `openclaw-plane-sdk` path dependency and that `packages/openclaw-plane-sdk` tests pass.

## File Structure

- Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/plane_tools.py`
  - Owns the gateway-backed tool operation names, request validation, safe defaults, confirmation guardrails, and httpx calls to the existing gateway routes.
- Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/plane_tool_cli.py`
  - Provides a local Codex-friendly CLI wrapper around `plane_tools.py` for read-first and marked smoke-ticket validation.
- Create `apps/openclaw-gateway/openclaw-gateway/tests/test_plane_tools.py`
  - Tests schema validation, auth propagation, read/search/list/create/update/comment behavior, default `Todo` state resolution, and `Ready for Agent` confirmation blocking.
- Create `apps/openclaw-gateway/openclaw-gateway/tests/test_plane_tool_cli.py`
  - Tests CLI argument parsing and secret-free output using a monkeypatched tool client.
- Create `apps/openclaw-gateway/chatgpt-actions/plane-openapi.yaml`
  - Defines the ChatGPT Action contract against `openclaw-gateway`, with only the approved narrow operation set.
- Create `apps/openclaw-gateway/chatgpt-actions/README.md`
  - Documents ChatGPT desktop/phone setup, auth, smoke flow, rollback, and limitations.
- Modify `apps/openclaw-gateway/README.md`
  - Link the ChatGPT/Codex tool adapter docs and state the non-secret boundary.
- Modify `apps/openclaw-gateway/openclaw-gateway/pyproject.toml`
  - Add a console script entry point for `openclaw-plane-tool`.

Do not edit real `.env` files. If new env vars become necessary, add only safe placeholders to `apps/openclaw-gateway/example.env`.

---

### Task 1: Tool Adapter Tests

**Files:**
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_plane_tools.py`

- [ ] **Step 1: Write failing tests for gateway-backed tool operations**

Create `test_plane_tools.py` with tests that use `respx` to assert every tool call goes to the gateway, carries only the gateway bearer token, and never needs the Plane API key:

```python
import httpx
import pytest
import respx

from openclaw_gateway.plane_tools import (
    PlaneToolAuth,
    PlaneToolClient,
    PlaneToolError,
    PlaneWorkItemCreateToolRequest,
    PlaneWorkItemUpdateToolRequest,
)


AUTH = PlaneToolAuth(
    gateway_url="http://gateway.example",
    gateway_token="gateway-secret",
)


@pytest.mark.asyncio
async def test_search_uses_gateway_auth_and_returns_items():
    with respx.mock(assert_all_called=True) as router:
        route = router.get("http://gateway.example/v1/workflow/plane/search").mock(
            return_value=httpx.Response(
                200,
                json={"items": [{"id": "work-item-1", "name": "Wire Plane tools"}]},
            )
        )

        result = await PlaneToolClient(AUTH).search_work_items(query="Plane", project_id="project-1", limit=5)

    assert result == {"items": [{"id": "work-item-1", "name": "Wire Plane tools"}]}
    assert route.calls.last.request.headers["Authorization"] == "Bearer gateway-secret"
    assert "X-API-Key" not in route.calls.last.request.headers
    assert dict(route.calls.last.request.url.params) == {
        "q": "Plane",
        "project_id": "project-1",
        "limit": "5",
    }


@pytest.mark.asyncio
async def test_create_resolves_todo_state_by_default():
    with respx.mock(assert_all_called=True) as router:
        router.get("http://gateway.example/v1/workflow/plane/projects/project-1/states").mock(
            return_value=httpx.Response(
                200,
                json={"items": [{"id": "state-todo", "name": "Todo", "group": "backlog"}]},
            )
        )
        create_route = router.post("http://gateway.example/v1/workflow/plane/projects/project-1/work-items").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "work-item-1",
                    "name": "[SMOKE][OPN-272] Chat-created ticket",
                    "project_id": "project-1",
                    "state_id": "state-todo",
                    "labels": [],
                },
            )
        )

        result = await PlaneToolClient(AUTH).create_work_item(
            project_id="project-1",
            request=PlaneWorkItemCreateToolRequest(
                name="[SMOKE][OPN-272] Chat-created ticket",
                description_html="<p>Smoke ticket.</p>",
            ),
        )

    assert result["state_id"] == "state-todo"
    assert create_route.calls.last.request.content
    assert create_route.calls.last.request.json()["state_id"] == "state-todo"


@pytest.mark.asyncio
async def test_ready_for_agent_requires_explicit_confirmation_and_checklist():
    client = PlaneToolClient(AUTH)

    with pytest.raises(PlaneToolError, match="Ready for Agent requires explicit confirmation"):
        await client.update_work_item(
            project_id="project-1",
            work_item_id="work-item-1",
            request=PlaneWorkItemUpdateToolRequest(state_name="Ready for Agent"),
        )


@pytest.mark.asyncio
async def test_ready_for_agent_update_resolves_state_when_confirmed():
    checklist = (
        "repo:docker label present; acceptance criteria present; verification command listed; "
        "rollback note present"
    )
    with respx.mock(assert_all_called=True) as router:
        router.get("http://gateway.example/v1/workflow/plane/projects/project-1/states").mock(
            return_value=httpx.Response(
                200,
                json={"items": [{"id": "state-ready", "name": "Ready for Agent"}]},
            )
        )
        patch_route = router.patch(
            "http://gateway.example/v1/workflow/plane/projects/project-1/work-items/work-item-1"
        ).mock(
            return_value=httpx.Response(
                200,
                json={"id": "work-item-1", "name": "Ready ticket", "state_id": "state-ready", "labels": []},
            )
        )

        result = await PlaneToolClient(AUTH).update_work_item(
            project_id="project-1",
            work_item_id="work-item-1",
            request=PlaneWorkItemUpdateToolRequest(
                state_name="Ready for Agent",
                ready_for_agent_confirmed=True,
                ready_for_agent_checklist=checklist,
            ),
        )

    assert result["state_id"] == "state-ready"
    assert patch_route.calls.last.request.json()["state_id"] == "state-ready"


@pytest.mark.asyncio
async def test_gateway_auth_failure_is_reported_without_secret():
    with respx.mock(assert_all_called=True) as router:
        router.get("http://gateway.example/v1/workflow/plane/projects").mock(
            return_value=httpx.Response(401, json={"detail": "Invalid bearer token"})
        )

        with pytest.raises(PlaneToolError) as exc_info:
            await PlaneToolClient(AUTH).list_projects()

    assert "gateway returned 401" in str(exc_info.value)
    assert "gateway-secret" not in str(exc_info.value)
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_plane_tools.py -q
```

Expected: fail with `ModuleNotFoundError: No module named 'openclaw_gateway.plane_tools'`.

---

### Task 2: Tool Adapter Implementation

**Files:**
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/plane_tools.py`

- [ ] **Step 1: Implement gateway-backed tool models and client**

Create `plane_tools.py`:

```python
from typing import Any, Literal

import httpx
from pydantic import AnyHttpUrl, BaseModel, Field


class PlaneToolError(RuntimeError):
    pass


class PlaneToolAuth(BaseModel):
    gateway_url: AnyHttpUrl
    gateway_token: str = Field(min_length=1)


class PlaneWorkItemCreateToolRequest(BaseModel):
    name: str = Field(min_length=1)
    description_html: str | None = None
    state_id: str | None = None
    state_name: str | None = None
    priority: Literal["urgent", "high", "medium", "low", "none"] | int | None = None
    label_ids: list[str] = Field(default_factory=list)
    assignee_ids: list[str] = Field(default_factory=list)
    parent_id: str | None = None


class PlaneWorkItemUpdateToolRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description_html: str | None = None
    state_id: str | None = None
    state_name: str | None = None
    priority: Literal["urgent", "high", "medium", "low", "none"] | int | None = None
    label_ids: list[str] | None = None
    assignee_ids: list[str] | None = None
    parent_id: str | None = None
    ready_for_agent_confirmed: bool = False
    ready_for_agent_checklist: str | None = None


class PlaneCommentToolRequest(BaseModel):
    comment_html: str = Field(min_length=1)


class PlaneToolClient:
    def __init__(self, auth: PlaneToolAuth, timeout_seconds: float = 15.0) -> None:
        self._base_url = str(auth.gateway_url).rstrip("/")
        self._token = auth.gateway_token
        self._timeout = httpx.Timeout(timeout_seconds)

    async def list_projects(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/workflow/plane/projects")

    async def list_states(self, project_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/workflow/plane/projects/{project_id}/states")

    async def list_labels(self, project_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/workflow/plane/projects/{project_id}/labels")

    async def search_work_items(
        self,
        *,
        query: str,
        project_id: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, str | int] = {"q": query}
        if project_id:
            params["project_id"] = project_id
        if limit is not None:
            params["limit"] = limit
        return await self._request("GET", "/v1/workflow/plane/search", params=params)

    async def list_project_work_items(self, *, project_id: str, limit: int | None = None) -> dict[str, Any]:
        params = {"limit": limit} if limit is not None else None
        return await self._request("GET", f"/v1/workflow/plane/projects/{project_id}/work-items", params=params)

    async def get_work_item(self, *, project_id: str, work_item_id: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/v1/workflow/plane/projects/{project_id}/work-items/{work_item_id}",
        )

    async def create_work_item(
        self,
        *,
        project_id: str,
        request: PlaneWorkItemCreateToolRequest,
    ) -> dict[str, Any]:
        payload = request.model_dump(exclude_none=True, exclude={"state_name"})
        if not payload.get("state_id"):
            payload["state_id"] = await self._resolve_state_id(project_id, request.state_name or "Todo")
        if request.state_name and request.state_name.casefold() == "ready for agent":
            raise PlaneToolError("New chat-created tickets must not auto-enter Ready for Agent")
        return await self._request(
            "POST",
            f"/v1/workflow/plane/projects/{project_id}/work-items",
            json=payload,
        )

    async def update_work_item(
        self,
        *,
        project_id: str,
        work_item_id: str,
        request: PlaneWorkItemUpdateToolRequest,
    ) -> dict[str, Any]:
        if request.state_name and request.state_name.casefold() == "ready for agent":
            checklist = request.ready_for_agent_checklist or ""
            if not request.ready_for_agent_confirmed or len(checklist.strip()) < 40:
                raise PlaneToolError(
                    "Ready for Agent requires explicit confirmation and complete checklist evidence"
                )
        payload = request.model_dump(
            exclude_none=True,
            exclude={
                "state_name",
                "ready_for_agent_confirmed",
                "ready_for_agent_checklist",
            },
        )
        if request.state_name and not payload.get("state_id"):
            payload["state_id"] = await self._resolve_state_id(project_id, request.state_name)
        return await self._request(
            "PATCH",
            f"/v1/workflow/plane/projects/{project_id}/work-items/{work_item_id}",
            json=payload,
        )

    async def add_comment(
        self,
        *,
        project_id: str,
        work_item_id: str,
        request: PlaneCommentToolRequest,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/v1/workflow/plane/projects/{project_id}/work-items/{work_item_id}/comments",
            json=request.model_dump(),
        )

    async def _resolve_state_id(self, project_id: str, state_name: str) -> str:
        states = await self.list_states(project_id)
        for state in states.get("items", []):
            if isinstance(state, dict) and str(state.get("name", "")).casefold() == state_name.casefold():
                state_id = state.get("id")
                if isinstance(state_id, str) and state_id:
                    return state_id
        raise PlaneToolError(f"Plane state not found: {state_name}")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str | int] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(
                    method,
                    f"{self._base_url}{path}",
                    headers={"Authorization": f"Bearer {self._token}"},
                    params=params,
                    json=json,
                )
        except httpx.TimeoutException as exc:
            raise PlaneToolError("gateway request timed out") from exc
        except httpx.HTTPError as exc:
            raise PlaneToolError("gateway request failed") from exc
        if response.is_error:
            raise PlaneToolError(f"gateway returned {response.status_code}")
        try:
            data = response.json()
        except ValueError as exc:
            raise PlaneToolError("gateway returned invalid json") from exc
        if not isinstance(data, dict):
            raise PlaneToolError("gateway returned unexpected payload")
        return data
```

- [ ] **Step 2: Run focused tests**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_plane_tools.py -q
```

Expected: all tests in `test_plane_tools.py` pass.

---

### Task 3: Codex CLI Tests

**Files:**
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_plane_tool_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Create `test_plane_tool_cli.py`:

```python
import json

import pytest

from openclaw_gateway import plane_tool_cli


class FakeClient:
    def __init__(self, auth, timeout_seconds=15.0):
        self.auth = auth

    async def search_work_items(self, **kwargs):
        return {"items": [{"id": "work-item-1", "name": kwargs["query"]}]}

    async def create_work_item(self, project_id, request):
        return {"id": "work-item-2", "name": request.name, "project_id": project_id, "state_id": "state-todo"}


def test_cli_search_outputs_json_without_token(monkeypatch, capsys):
    monkeypatch.setenv("GATEWAY_URL", "http://gateway.example")
    monkeypatch.setenv("GATEWAY_AUTH_TOKEN", "gateway-secret")
    monkeypatch.setattr(plane_tool_cli, "PlaneToolClient", FakeClient)

    exit_code = plane_tool_cli.main(["search", "--query", "Plane", "--project-id", "project-1"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert json.loads(output)["items"][0]["name"] == "Plane"
    assert "gateway-secret" not in output


def test_cli_requires_gateway_env(monkeypatch, capsys):
    monkeypatch.delenv("GATEWAY_URL", raising=False)
    monkeypatch.delenv("GATEWAY_AUTH_TOKEN", raising=False)

    exit_code = plane_tool_cli.main(["projects"])

    assert exit_code == 2
    assert "GATEWAY_URL and GATEWAY_AUTH_TOKEN are required" in capsys.readouterr().err


def test_cli_create_requires_project_id(monkeypatch):
    monkeypatch.setenv("GATEWAY_URL", "http://gateway.example")
    monkeypatch.setenv("GATEWAY_AUTH_TOKEN", "gateway-secret")
    monkeypatch.setattr(plane_tool_cli, "PlaneToolClient", FakeClient)

    with pytest.raises(SystemExit) as exc_info:
        plane_tool_cli.main(["create", "--name", "Missing project"])

    assert exc_info.value.code == 2
```

- [ ] **Step 2: Run and confirm failure**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_plane_tool_cli.py -q
```

Expected: fail with `ImportError` because `plane_tool_cli.py` does not exist.

---

### Task 4: Codex CLI Implementation

**Files:**
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/plane_tool_cli.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/pyproject.toml`

- [ ] **Step 1: Implement the CLI module**

Create `plane_tool_cli.py`:

```python
import argparse
import asyncio
import json
import os
import sys
from typing import Any

from openclaw_gateway.plane_tools import (
    PlaneCommentToolRequest,
    PlaneToolAuth,
    PlaneToolClient,
    PlaneToolError,
    PlaneWorkItemCreateToolRequest,
    PlaneWorkItemUpdateToolRequest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="openclaw-plane-tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("projects")

    states = subparsers.add_parser("states")
    states.add_argument("--project-id", required=True)

    labels = subparsers.add_parser("labels")
    labels.add_argument("--project-id", required=True)

    search = subparsers.add_parser("search")
    search.add_argument("--query", required=True)
    search.add_argument("--project-id")
    search.add_argument("--limit", type=int)

    read = subparsers.add_parser("read")
    read.add_argument("--project-id", required=True)
    read.add_argument("--work-item-id", required=True)

    create = subparsers.add_parser("create")
    create.add_argument("--project-id", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--description-html")
    create.add_argument("--state-name")
    create.add_argument("--priority")

    update = subparsers.add_parser("update")
    update.add_argument("--project-id", required=True)
    update.add_argument("--work-item-id", required=True)
    update.add_argument("--name")
    update.add_argument("--description-html")
    update.add_argument("--state-name")
    update.add_argument("--priority")
    update.add_argument("--ready-for-agent-confirmed", action="store_true")
    update.add_argument("--ready-for-agent-checklist")

    comment = subparsers.add_parser("comment")
    comment.add_argument("--project-id", required=True)
    comment.add_argument("--work-item-id", required=True)
    comment.add_argument("--comment-html", required=True)

    return parser


async def run(args: argparse.Namespace) -> dict[str, Any]:
    gateway_url = os.environ.get("GATEWAY_URL")
    gateway_token = os.environ.get("GATEWAY_AUTH_TOKEN")
    if not gateway_url or not gateway_token:
        raise PlaneToolError("GATEWAY_URL and GATEWAY_AUTH_TOKEN are required")

    client = PlaneToolClient(PlaneToolAuth(gateway_url=gateway_url, gateway_token=gateway_token))
    if args.command == "projects":
        return await client.list_projects()
    if args.command == "states":
        return await client.list_states(args.project_id)
    if args.command == "labels":
        return await client.list_labels(args.project_id)
    if args.command == "search":
        return await client.search_work_items(query=args.query, project_id=args.project_id, limit=args.limit)
    if args.command == "read":
        return await client.get_work_item(project_id=args.project_id, work_item_id=args.work_item_id)
    if args.command == "create":
        return await client.create_work_item(
            project_id=args.project_id,
            request=PlaneWorkItemCreateToolRequest(
                name=args.name,
                description_html=args.description_html,
                state_name=args.state_name,
                priority=args.priority,
            ),
        )
    if args.command == "update":
        return await client.update_work_item(
            project_id=args.project_id,
            work_item_id=args.work_item_id,
            request=PlaneWorkItemUpdateToolRequest(
                name=args.name,
                description_html=args.description_html,
                state_name=args.state_name,
                priority=args.priority,
                ready_for_agent_confirmed=args.ready_for_agent_confirmed,
                ready_for_agent_checklist=args.ready_for_agent_checklist,
            ),
        )
    if args.command == "comment":
        return await client.add_comment(
            project_id=args.project_id,
            work_item_id=args.work_item_id,
            request=PlaneCommentToolRequest(comment_html=args.comment_html),
        )
    raise PlaneToolError(f"unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = asyncio.run(run(args))
    except PlaneToolError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Add the console script**

In `apps/openclaw-gateway/openclaw-gateway/pyproject.toml`, add:

```toml
[project.scripts]
openclaw-plane-tool = "openclaw_gateway.plane_tool_cli:main"
```

- [ ] **Step 3: Run focused CLI tests**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_plane_tool_cli.py -q
```

Expected: all CLI tests pass.

---

### Task 5: ChatGPT Action Contract

**Files:**
- Create: `apps/openclaw-gateway/chatgpt-actions/plane-openapi.yaml`
- Create: `apps/openclaw-gateway/chatgpt-actions/README.md`

- [ ] **Step 1: Add the OpenAPI Action document**

Create `plane-openapi.yaml` with the gateway endpoints ChatGPT may call:

```yaml
openapi: 3.1.0
info:
  title: OpenClaw Plane Tools
  version: 0.1.0
  description: Gateway-backed Plane ticket operations for OpenClaw.
servers:
  - url: https://openclaw-gateway.home.lab
security:
  - gatewayBearer: []
components:
  securitySchemes:
    gatewayBearer:
      type: http
      scheme: bearer
  schemas:
    PlaneWorkItemCreate:
      type: object
      required: [name]
      additionalProperties: false
      properties:
        name:
          type: string
          minLength: 1
        description_html:
          type: string
        state_id:
          type: string
          description: Optional explicit Plane state UUID. Omit to use Todo.
        priority:
          oneOf:
            - type: string
              enum: [urgent, high, medium, low, none]
            - type: integer
        label_ids:
          type: array
          items:
            type: string
        assignee_ids:
          type: array
          items:
            type: string
        parent_id:
          type: string
    PlaneWorkItemUpdate:
      type: object
      additionalProperties: false
      properties:
        name:
          type: string
          minLength: 1
        description_html:
          type: string
        state_id:
          type: string
        priority:
          oneOf:
            - type: string
              enum: [urgent, high, medium, low, none]
            - type: integer
        label_ids:
          type: array
          items:
            type: string
        assignee_ids:
          type: array
          items:
            type: string
        parent_id:
          type: string
    PlaneCommentCreate:
      type: object
      required: [comment_html]
      additionalProperties: false
      properties:
        comment_html:
          type: string
          minLength: 1
paths:
  /v1/workflow/plane/projects:
    get:
      operationId: listPlaneProjects
      summary: List Plane projects.
      responses:
        "200":
          description: Project list.
  /v1/workflow/plane/projects/{project_id}/states:
    get:
      operationId: listPlaneStates
      summary: List states for a Plane project.
      parameters:
        - name: project_id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: State list.
  /v1/workflow/plane/projects/{project_id}/labels:
    get:
      operationId: listPlaneLabels
      summary: List labels for a Plane project.
      parameters:
        - name: project_id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: Label list.
  /v1/workflow/plane/search:
    get:
      operationId: searchPlaneWorkItems
      summary: Search Plane work items.
      parameters:
        - name: q
          in: query
          required: true
          schema:
            type: string
            minLength: 1
        - name: project_id
          in: query
          required: false
          schema:
            type: string
        - name: limit
          in: query
          required: false
          schema:
            type: integer
            minimum: 1
            maximum: 100
      responses:
        "200":
          description: Search results.
  /v1/workflow/plane/projects/{project_id}/work-items/{work_item_id}:
    get:
      operationId: getPlaneWorkItem
      summary: Read a Plane work item.
      parameters:
        - name: project_id
          in: path
          required: true
          schema:
            type: string
        - name: work_item_id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: Work item.
    patch:
      operationId: updatePlaneWorkItem
      summary: Update a specific Plane work item. Do not use for delete/archive/bulk edits.
      parameters:
        - name: project_id
          in: path
          required: true
          schema:
            type: string
        - name: work_item_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/PlaneWorkItemUpdate"
      responses:
        "200":
          description: Updated work item.
  /v1/workflow/plane/projects/{project_id}/work-items:
    get:
      operationId: listPlaneProjectWorkItems
      summary: List Plane work items in a project.
      parameters:
        - name: project_id
          in: path
          required: true
          schema:
            type: string
        - name: limit
          in: query
          required: false
          schema:
            type: integer
            minimum: 1
            maximum: 100
      responses:
        "200":
          description: Work item list.
    post:
      operationId: createPlaneWorkItem
      summary: Create a Plane work item. New chat-created tickets must default to Todo unless a human supplies another non-Ready state.
      parameters:
        - name: project_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/PlaneWorkItemCreate"
      responses:
        "200":
          description: Created work item.
  /v1/workflow/plane/projects/{project_id}/work-items/{work_item_id}/comments:
    post:
      operationId: commentOnPlaneWorkItem
      summary: Add a comment to a specific Plane work item.
      parameters:
        - name: project_id
          in: path
          required: true
          schema:
            type: string
        - name: work_item_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/PlaneCommentCreate"
      responses:
        "200":
          description: Created comment.
```

- [ ] **Step 2: Add setup and smoke docs**

Create `apps/openclaw-gateway/chatgpt-actions/README.md`:

```markdown
# ChatGPT Plane Action

This directory contains the ChatGPT Action contract for OPN-272. It calls the existing `openclaw-gateway` Plane routes and uses the gateway bearer token. Do not give ChatGPT the Plane API key.

## Setup

1. Expose `openclaw-gateway` through the existing Nginx Proxy Manager and Authentik pattern if external ChatGPT access is required.
2. Import `plane-openapi.yaml` into the ChatGPT Action builder.
3. Configure bearer authentication with `GATEWAY_AUTH_TOKEN` from the gateway runtime secret store.
4. Keep the Plane API key only in the gateway runtime environment.

## Read-First Smoke

1. Run `listPlaneProjects`.
2. Run `listPlaneStates` for the intended Openclaw project.
3. Confirm the `Todo` state ID.
4. Run `searchPlaneWorkItems` for `OPN-272`.

Stop if any read operation fails.

## Write Smoke

Create exactly one marked smoke ticket:

```text
[SMOKE][OPN-272] ChatGPT Plane action create smoke
```

Expected behavior:

- The ticket is created in the intended Openclaw project.
- The ticket starts in `Todo`.
- A follow-up comment can be added to the same ticket.
- A narrow update can be made to the same ticket.
- No delete, archive, or bulk operation exists.
- Gateway logs include the create/comment/update audit records.

## Phone Validation

From the ChatGPT phone app, ask to create the same marked smoke ticket in the intended project. Confirm it lands in `Todo` and can be searched/read afterward.

## Rollback

Disable or remove the ChatGPT Action registration. Plane itself and the gateway routes do not need to be rolled back for Action-only failures.
```

---

### Task 6: Docs And README Link

**Files:**
- Modify: `apps/openclaw-gateway/README.md`

- [ ] **Step 1: Document the tool adapter boundary**

Add this paragraph after the Plane SDK section:

```markdown
## ChatGPT/Codex Plane Tools

OPN-272 adds a gateway-backed tool adapter for ChatGPT and Codex. The local Codex path uses `openclaw-plane-tool`, and the ChatGPT path uses `chatgpt-actions/plane-openapi.yaml`. Both paths call only the existing authenticated `/v1/workflow/plane/...` gateway routes with the gateway bearer token. They must not receive the Plane API key, raw upstream Plane payloads, Docker access, or broad delete/archive/bulk-update capabilities.
```

---

### Task 7: Focused Verification

**Files:**
- Modify: `docs/superpowers/plans/2026-07-12-opn-272-chatgpt-codex-plane-tools.md`

- [ ] **Step 1: Run unit tests**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_plane_tools.py tests/test_plane_tool_cli.py tests/test_workflow_routes.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run SDK tests**

Run:

```bash
cd packages/openclaw-plane-sdk
python -m pytest tests/test_plane_client.py -q
```

Expected: all SDK tests pass.

- [ ] **Step 3: Validate Compose without deployment**

Run from repo root:

```bash
docker compose -f apps/openclaw-gateway/compose.yml --env-file apps/openclaw-gateway/example.env config --quiet
```

Expected: exits 0. This must not deploy or restart containers.

- [ ] **Step 4: Check diff hygiene**

Run from repo root:

```bash
git diff --check
```

Expected: exits 0.

- [ ] **Step 5: Scan changed files for obvious secrets**

Run from repo root:

```bash
git diff -- apps/openclaw-gateway docs/superpowers/plans/2026-07-12-opn-272-chatgpt-codex-plane-tools.md | rg -n "GATEWAY_AUTH_TOKEN=|PLANE_API_KEY=|gateway-secret|plane-secret|Bearer [A-Za-z0-9]"
```

Expected: only safe placeholders or test sentinel strings appear. Do not print or copy real `.env` values.

---

### Task 8: Local Codex Smoke

**Files:**
- No repo file changes expected unless smoke evidence is intentionally documented afterward.

- [ ] **Step 1: Export runtime env without printing secrets**

Use a shell with real values loaded from the operator’s secret store:

```bash
export GATEWAY_URL="https://openclaw-gateway.home.lab"
export GATEWAY_AUTH_TOKEN="<real token from secret store>"
```

Do not commit or print the token.

- [ ] **Step 2: Read-first smoke**

Run:

```bash
openclaw-plane-tool projects
openclaw-plane-tool states --project-id "<openclaw-project-id>"
openclaw-plane-tool search --query "OPN-272" --project-id "<openclaw-project-id>" --limit 5
```

Expected: all commands return JSON and do not print `GATEWAY_AUTH_TOKEN`.

- [ ] **Step 3: Write smoke with a marked ticket**

Run:

```bash
openclaw-plane-tool create \
  --project-id "<openclaw-project-id>" \
  --name "[SMOKE][OPN-272] Codex Plane tool create smoke" \
  --description-html "<p>Created by OPN-272 local Codex smoke.</p>"
```

Expected: ticket is created in `Todo`. Capture the returned work item ID without committing it if it is environment-specific.

- [ ] **Step 4: Comment and narrow update smoke**

Run:

```bash
openclaw-plane-tool comment \
  --project-id "<openclaw-project-id>" \
  --work-item-id "<smoke-work-item-id>" \
  --comment-html "<p>OPN-272 local Codex smoke comment.</p>"

openclaw-plane-tool update \
  --project-id "<openclaw-project-id>" \
  --work-item-id "<smoke-work-item-id>" \
  --name "[SMOKE][OPN-272] Codex Plane tool update smoke"
```

Expected: both calls succeed and gateway logs include the existing audit records.

---

### Task 9: ChatGPT Desktop And Phone Smoke

**Files:**
- No repo file changes expected unless documenting evidence.

- [ ] **Step 1: Configure ChatGPT Action**

Import `apps/openclaw-gateway/chatgpt-actions/plane-openapi.yaml` into the ChatGPT Action builder and configure bearer auth with the gateway token. If external access is required, complete the external UI checklist:

- Komodo redeploy for gateway changes.
- Nginx Proxy Manager proxy host for the gateway Action URL.
- AdGuard DNS entry if using `*.home.lab`.
- Authentik policy/outpost only if compatible with ChatGPT Action access.

- [ ] **Step 2: Desktop read-first smoke**

From ChatGPT desktop, run project/state/search operations first. Expected: all return valid Plane data.

- [ ] **Step 3: Desktop write smoke**

From ChatGPT desktop, create exactly one ticket named:

```text
[SMOKE][OPN-272] ChatGPT desktop Plane action create smoke
```

Expected: created in the intended Openclaw project in `Todo`, then read back by search.

- [ ] **Step 4: Phone smoke**

From ChatGPT phone, create exactly one ticket named:

```text
[SMOKE][OPN-272] ChatGPT phone Plane action create smoke
```

Expected: created in the intended Openclaw project in `Todo`, then visible from desktop/search.

- [ ] **Step 5: Audit evidence**

Use read-only Docker inspection only:

```bash
docker logs <openclaw-gateway-container> | rg "plane workflow write audit|OPN-272"
```

Expected: create/comment/update audit records exist and do not contain bearer tokens, Plane API keys, request bodies, or raw upstream payloads.

---

### Task 10: Final Linear Update

**Files:**
- No code changes.

- [ ] **Step 1: Commit after verification**

Commit only the OPN-272 files:

```bash
git add \
  apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/plane_tools.py \
  apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/plane_tool_cli.py \
  apps/openclaw-gateway/openclaw-gateway/tests/test_plane_tools.py \
  apps/openclaw-gateway/openclaw-gateway/tests/test_plane_tool_cli.py \
  apps/openclaw-gateway/openclaw-gateway/pyproject.toml \
  apps/openclaw-gateway/chatgpt-actions/plane-openapi.yaml \
  apps/openclaw-gateway/chatgpt-actions/README.md \
  apps/openclaw-gateway/README.md \
  docs/superpowers/plans/2026-07-12-opn-272-chatgpt-codex-plane-tools.md
git commit -m "OPN-272: add Plane chat tool surface"
```

Do not stage unrelated dirty files in the current worktree.

- [ ] **Step 2: Update Linear**

Add a final Linear comment with:

- Outcome.
- Files changed.
- Verification commands and results.
- Commit hash.
- Local Codex smoke result.
- ChatGPT desktop smoke result.
- ChatGPT phone smoke result.
- Remaining follow-ups, or `None`.

If ChatGPT Action setup cannot be completed because the gateway URL/auth path is not externally reachable, leave OPN-272 active or blocked with the exact external dependency and evidence. Do not mark `Done` until desktop and phone acceptance criteria are satisfied.

---

## Self-Review

- Spec coverage: The plan covers search, read, create, update, comment, list projects/states/labels, auth, permissions, audit evidence, desktop smoke, phone smoke, setup docs, tests, and rollback.
- Placeholder scan: The only angle-bracket placeholders are live smoke values that must come from the operator's secret store or live Plane project. No implementation step uses unspecified code.
- Type consistency: Tool model names and CLI calls are consistent across tests and implementation steps.
