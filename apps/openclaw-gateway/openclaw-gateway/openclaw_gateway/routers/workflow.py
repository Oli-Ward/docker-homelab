from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from openclaw_gateway.auth import require_gateway_token
from openclaw_gateway.clients.plane import PlaneClient, PlaneResponseError
from openclaw_gateway.schemas.workflow import (
    PlaneComment,
    PlaneCommentCreate,
    PlaneLabelsResponse,
    PlaneProjectsResponse,
    PlaneStatesResponse,
    PlaneWorkItem,
    PlaneWorkItemCreate,
    PlaneWorkItemsResponse,
    PlaneWorkItemUpdate,
)
from openclaw_gateway.settings import GatewaySettings


ResponseT = TypeVar("ResponseT")


async def _map_plane_errors(request: Callable[[], Awaitable[ResponseT]]) -> ResponseT:
    try:
        return await request()
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="plane timed out",
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"plane returned {exc.response.status_code}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="plane request failed",
        ) from exc
    except PlaneResponseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="plane returned an invalid response",
        ) from exc


def build_workflow_router(settings: GatewaySettings) -> APIRouter:
    router = APIRouter(
        prefix="/v1/workflow",
        dependencies=[Depends(require_gateway_token(settings))],
    )

    def plane_client() -> PlaneClient:
        return PlaneClient(
            base_url=str(settings.plane_api_base_url),
            api_key=settings.plane_api_key,
            workspace_slug=settings.plane_workspace_slug,
            timeout_seconds=settings.upstream_timeout_seconds,
        )

    @router.get("/plane/projects")
    async def plane_projects() -> PlaneProjectsResponse:
        return await _map_plane_errors(plane_client().list_projects)

    @router.get("/plane/projects/{project_id}/states")
    async def plane_states(project_id: str) -> PlaneStatesResponse:
        return await _map_plane_errors(lambda: plane_client().list_states(project_id))

    @router.get("/plane/projects/{project_id}/labels")
    async def plane_labels(project_id: str) -> PlaneLabelsResponse:
        return await _map_plane_errors(lambda: plane_client().list_labels(project_id))

    @router.get("/plane/search")
    async def plane_search(
        q: str = Query(min_length=1),
        project_id: str | None = None,
        limit: int | None = Query(default=None, ge=1, le=100),
    ) -> PlaneWorkItemsResponse:
        return await _map_plane_errors(
            lambda: plane_client().search_work_items(
                query=q,
                project_id=project_id,
                limit=limit,
            )
        )

    @router.get("/plane/projects/{project_id}/work-items")
    async def plane_project_work_items(
        project_id: str,
        limit: int | None = Query(default=None, ge=1, le=100),
    ) -> PlaneWorkItemsResponse:
        return await _map_plane_errors(
            lambda: plane_client().list_project_work_items(project_id=project_id, limit=limit)
        )

    @router.get("/plane/projects/{project_id}/work-items/{work_item_id}")
    async def plane_work_item(project_id: str, work_item_id: str) -> PlaneWorkItem:
        return await _map_plane_errors(
            lambda: plane_client().get_work_item(project_id=project_id, work_item_id=work_item_id)
        )

    @router.post("/plane/projects/{project_id}/work-items")
    async def plane_create_work_item(
        project_id: str,
        work_item: PlaneWorkItemCreate,
    ) -> PlaneWorkItem:
        return await _map_plane_errors(
            lambda: plane_client().create_work_item(project_id=project_id, work_item=work_item)
        )

    @router.patch("/plane/projects/{project_id}/work-items/{work_item_id}")
    async def plane_update_work_item(
        project_id: str,
        work_item_id: str,
        update: PlaneWorkItemUpdate,
    ) -> PlaneWorkItem:
        return await _map_plane_errors(
            lambda: plane_client().update_work_item(
                project_id=project_id,
                work_item_id=work_item_id,
                update=update,
            )
        )

    @router.post("/plane/projects/{project_id}/work-items/{work_item_id}/comments")
    async def plane_add_comment(
        project_id: str,
        work_item_id: str,
        comment: PlaneCommentCreate,
    ) -> PlaneComment:
        return await _map_plane_errors(
            lambda: plane_client().add_comment(
                project_id=project_id,
                work_item_id=work_item_id,
                comment=comment,
            )
        )

    return router
