from collections.abc import Awaitable, Callable
import hashlib
import hmac
import json
from typing import TypeVar

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from openclaw_gateway.auth import require_gateway_token
from openclaw_gateway.clients.plane import PlaneApiError, PlaneClient, PlaneResponseError
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
    PlaneWebhookAck,
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
    except PlaneApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"plane returned {exc.status_code}",
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


def build_plane_webhook_router(settings: GatewaySettings) -> APIRouter:
    router = APIRouter(prefix="/v1/workflow")

    @router.post("/plane/webhook")
    async def plane_webhook(
        request: Request,
        x_plane_delivery: str | None = Header(default=None),
        x_plane_signature: str | None = Header(default=None),
    ) -> PlaneWebhookAck:
        if not settings.plane_webhook_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="plane webhook secret is not configured",
            )
        if not x_plane_delivery:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="missing plane delivery id",
            )
        if not x_plane_signature:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="invalid plane signature",
            )

        try:
            payload = await request.json()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid plane webhook json",
            ) from exc

        expected_signature = hmac.new(
            settings.plane_webhook_secret.encode("utf-8"),
            msg=json.dumps(payload).encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_signature, x_plane_signature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="invalid plane signature",
            )

        data = payload.get("data") if isinstance(payload, dict) else None
        resource_id = data.get("id") if isinstance(data, dict) else None
        return PlaneWebhookAck(
            accepted=True,
            delivery_id=x_plane_delivery,
            event=payload.get("event") if isinstance(payload, dict) else None,
            action=payload.get("action") if isinstance(payload, dict) else None,
            resource_id=str(resource_id) if resource_id is not None else None,
            webhook_id=payload.get("webhook_id") if isinstance(payload, dict) else None,
        )

    return router
