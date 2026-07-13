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

    async def list_project_work_items(
        self,
        *,
        project_id: str,
        limit: int | None = None,
    ) -> dict[str, Any]:
        params = {"limit": limit} if limit is not None else None
        return await self._request(
            "GET",
            f"/v1/workflow/plane/projects/{project_id}/work-items",
            params=params,
        )

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
        if _is_ready_for_agent(request.state_name):
            raise PlaneToolError("New chat-created tickets must not auto-enter Ready for Agent")

        payload = request.model_dump(exclude_none=True, exclude={"state_name"})
        if not payload.get("state_id"):
            payload["state_id"] = await self._resolve_state_id(project_id, request.state_name or "Todo")
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
        if _is_ready_for_agent(request.state_name):
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


def _is_ready_for_agent(state_name: str | None) -> bool:
    return bool(state_name and state_name.casefold() == "ready for agent")
