from typing import Any

import httpx

from openclaw_plane_sdk.models import (
    PlaneComment,
    PlaneCommentCreate,
    PlaneLabel,
    PlaneLabelsResponse,
    PlaneProject,
    PlaneProjectsResponse,
    PlaneState,
    PlaneStatesResponse,
    PlaneWorkItem,
    PlaneWorkItemCreate,
    PlaneWorkItemsResponse,
    PlaneWorkItemUpdate,
)


class PlaneResponseError(RuntimeError):
    pass


class PlaneApiError(RuntimeError):
    def __init__(self, status_code: int, kind: str) -> None:
        self.status_code = status_code
        self.kind = kind
        super().__init__(f"plane returned {status_code} ({kind})")


class PlaneClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        workspace_slug: str,
        timeout_seconds: float,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._workspace_slug = workspace_slug
        self._timeout = httpx.Timeout(timeout_seconds)

    async def list_projects(self) -> PlaneProjectsResponse:
        payload = await self._get(f"/api/v1/workspaces/{self._workspace_slug}/projects/")
        return PlaneProjectsResponse(items=[self._project(item) for item in self._items(payload)])

    async def list_states(self, project_id: str) -> PlaneStatesResponse:
        payload = await self._get(
            f"/api/v1/workspaces/{self._workspace_slug}/projects/{project_id}/states/"
        )
        return PlaneStatesResponse(items=[self._state(item) for item in self._items(payload)])

    async def list_labels(self, project_id: str) -> PlaneLabelsResponse:
        payload = await self._get(
            f"/api/v1/workspaces/{self._workspace_slug}/projects/{project_id}/labels/"
        )
        return PlaneLabelsResponse(items=[self._label(item) for item in self._items(payload)])

    async def search_work_items(
        self,
        query: str,
        project_id: str | None = None,
        limit: int | None = None,
    ) -> PlaneWorkItemsResponse:
        params: dict[str, str | int] = {"search": query}
        if project_id:
            params["project_id"] = project_id
        if limit:
            params["limit"] = limit

        payload = await self._get(
            f"/api/v1/workspaces/{self._workspace_slug}/work-items/search/",
            params=params,
        )
        return PlaneWorkItemsResponse(items=[self._work_item(item) for item in self._items(payload)])

    async def list_project_work_items(
        self,
        project_id: str,
        limit: int | None = None,
    ) -> PlaneWorkItemsResponse:
        params = {"per_page": limit} if limit else None
        payload = await self._get(
            f"/api/v1/workspaces/{self._workspace_slug}/projects/{project_id}/work-items/",
            params=params,
        )
        return PlaneWorkItemsResponse(items=[self._work_item(item) for item in self._items(payload)])

    async def get_work_item(self, project_id: str, work_item_id: str) -> PlaneWorkItem:
        payload = await self._get(
            f"/api/v1/workspaces/{self._workspace_slug}/projects/{project_id}/work-items/{work_item_id}/"
        )
        return self._work_item(payload)

    async def create_work_item(
        self,
        project_id: str,
        work_item: PlaneWorkItemCreate,
    ) -> PlaneWorkItem:
        payload = await self._post(
            f"/api/v1/workspaces/{self._workspace_slug}/projects/{project_id}/work-items/",
            json=work_item.model_dump(exclude_none=True, exclude_defaults=True),
        )
        return self._work_item(payload)

    async def update_work_item(
        self,
        project_id: str,
        work_item_id: str,
        update: PlaneWorkItemUpdate,
    ) -> PlaneWorkItem:
        payload = update.model_dump(exclude_unset=True)
        if "state_id" in payload:
            payload["state"] = payload.pop("state_id")
        payload = await self._patch(
            f"/api/v1/workspaces/{self._workspace_slug}/projects/{project_id}/work-items/{work_item_id}/",
            json=payload,
        )
        return self._work_item(payload)

    async def add_comment(
        self,
        project_id: str,
        work_item_id: str,
        comment: PlaneCommentCreate,
    ) -> PlaneComment:
        payload = await self._post(
            f"/api/v1/workspaces/{self._workspace_slug}/projects/{project_id}/work-items/{work_item_id}/comments/",
            json=comment.model_dump(),
        )
        return PlaneComment(
            id=str(payload.get("id", "")),
            comment_html=payload.get("comment_html") or payload.get("comment"),
            raw=payload,
        )

    async def _get(
        self,
        path: str,
        params: dict[str, str | int] | None = None,
    ) -> Any:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}{path}",
                headers=self._headers(),
                params=params,
            )
            return self._response_json(response)

    async def _post(self, path: str, json: dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}{path}",
                headers=self._headers(),
                json=json,
            )
            return self._response_json(response)

    async def _patch(self, path: str, json: dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.patch(
                f"{self._base_url}{path}",
                headers=self._headers(),
                json=json,
            )
            return self._response_json(response)

    def _response_json(self, response: httpx.Response) -> Any:
        if response.is_error:
            raise PlaneApiError(
                status_code=response.status_code,
                kind=self._error_kind(response.status_code),
            )
        if not response.content:
            raise PlaneResponseError("plane returned empty response")
        try:
            return response.json()
        except ValueError as exc:
            raise PlaneResponseError("plane returned invalid json response") from exc

    def _error_kind(self, status_code: int) -> str:
        if status_code in {401, 403}:
            return "auth"
        if status_code == 404:
            return "not_found"
        if status_code == 429:
            return "rate_limited"
        if status_code >= 500:
            return "server"
        return "client"

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self._api_key}

    def _items(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if not isinstance(payload, dict):
            return []

        for key in ("results", "items", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        return []

    def _project(self, item: dict[str, Any]) -> PlaneProject:
        return PlaneProject(
            id=str(item.get("id", "")),
            name=str(item.get("name", "")),
            identifier=item.get("identifier"),
            raw=item,
        )

    def _state(self, item: dict[str, Any]) -> PlaneState:
        return PlaneState(
            id=str(item.get("id", "")),
            name=str(item.get("name", "")),
            group=item.get("group"),
            raw=item,
        )

    def _label(self, item: dict[str, Any]) -> PlaneLabel:
        return PlaneLabel(
            id=str(item.get("id", "")),
            name=str(item.get("name", "")),
            color=item.get("color"),
            raw=item,
        )

    def _work_item(self, item: dict[str, Any]) -> PlaneWorkItem:
        labels = item.get("labels") or item.get("label_details") or []
        return PlaneWorkItem(
            id=str(item.get("id", "")),
            name=str(item.get("name", "")),
            project_id=item.get("project_id") or item.get("project"),
            sequence_id=item.get("sequence_id"),
            state_id=item.get("state_id") or item.get("state"),
            priority=item.get("priority"),
            labels=[
                {"id": label.get("id"), "name": str(label.get("name", ""))}
                for label in labels
                if isinstance(label, dict)
            ],
            raw=item,
        )
