from collections.abc import Awaitable, Callable
import hashlib
import hmac
import json
import logging
from typing import TypeVar

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from openclaw_gateway.auth import require_gateway_token
from openclaw_gateway.clients.n8n import N8nClient
from openclaw_gateway.clients.plane import PlaneApiError, PlaneClient, PlaneResponseError
from openclaw_gateway.plane_webhooks import FilePlaneWebhookQueue, PlaneWebhookQueueError
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
    PlaneWebhookDispatchResponse,
    PlaneWebhookQueueStatusResponse,
)
from openclaw_gateway.settings import GatewaySettings


ResponseT = TypeVar("ResponseT")
logger = logging.getLogger(__name__)


def _extract_plane_actor_id(payload: dict) -> str | None:
    for field_name in ("actor", "updated_by", "created_by", "owned_by"):
        actor = payload.get(field_name)
        if isinstance(actor, dict):
            actor_id = actor.get("id")
            if isinstance(actor_id, str) and actor_id:
                return actor_id
        if isinstance(actor, str) and actor:
            return actor
    return None


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

    def n8n_client() -> N8nClient:
        return N8nClient(
            base_url=str(settings.n8n_webhook_base_url),
            smoke_path=settings.n8n_openclaw_smoke_path,
            rating_prompt_path=settings.n8n_jellyfin_rating_prompt_path,
            plane_dispatch_path=settings.n8n_plane_webhook_dispatch_path,
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

    @router.get("/plane/webhook/queue")
    async def plane_webhook_queue_status() -> PlaneWebhookQueueStatusResponse:
        try:
            queue_status = FilePlaneWebhookQueue(
                queue_path=settings.plane_webhook_queue_path,
                dedupe_path=settings.plane_webhook_dedupe_path,
            ).status(configured=bool(settings.plane_webhook_secret))
        except PlaneWebhookQueueError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="plane webhook queue is unavailable",
            ) from exc
        return PlaneWebhookQueueStatusResponse(**queue_status.model_dump())

    @router.post("/plane/webhook/dispatch")
    async def plane_webhook_dispatch(
        limit: int = Query(default=10, ge=1, le=100),
    ) -> PlaneWebhookDispatchResponse:
        queue = FilePlaneWebhookQueue(
            queue_path=settings.plane_webhook_queue_path,
            dedupe_path=settings.plane_webhook_dedupe_path,
        )
        try:
            pending_events = queue.pending_events(limit=limit)
        except PlaneWebhookQueueError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="plane webhook queue is unavailable",
            ) from exc

        dispatched_delivery_ids: list[str] = []
        for event in pending_events:
            delivery_id = event.get("delivery_id")
            if not isinstance(delivery_id, str):
                continue
            try:
                await n8n_client().forward_plane_webhook_event(event)
                queue.mark_dispatched(delivery_id)
            except PlaneWebhookQueueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="plane webhook queue is unavailable",
                ) from exc
            except httpx.TimeoutException as exc:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"plane webhook dispatch timed out for {delivery_id}",
                ) from exc
            except httpx.HTTPStatusError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"plane webhook dispatch returned {exc.response.status_code} for {delivery_id}",
                ) from exc
            except httpx.HTTPError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"plane webhook dispatch failed for {delivery_id}",
                ) from exc
            dispatched_delivery_ids.append(delivery_id)

        try:
            remaining_pending = len(queue.pending_events(limit=101))
        except PlaneWebhookQueueError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="plane webhook queue is unavailable",
            ) from exc
        return PlaneWebhookDispatchResponse(
            dispatched_count=len(dispatched_delivery_ids),
            pending_count=remaining_pending,
            delivery_ids=dispatched_delivery_ids,
        )

    return router


def build_plane_webhook_router(settings: GatewaySettings) -> APIRouter:
    router = APIRouter(prefix="/v1/workflow")

    @router.post("/plane/webhook", response_model_exclude_none=True)
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

        correlation_id = f"plane:{x_plane_delivery}"
        data = payload.get("data") if isinstance(payload, dict) else None
        resource_id = data.get("id") if isinstance(data, dict) else None
        actor_id = _extract_plane_actor_id(payload) if isinstance(payload, dict) else None
        normalized_event = {
            "correlation_id": correlation_id,
            "delivery_id": x_plane_delivery,
            "event": payload.get("event") if isinstance(payload, dict) else None,
            "action": payload.get("action") if isinstance(payload, dict) else None,
            "resource_id": str(resource_id) if resource_id is not None else None,
            "webhook_id": payload.get("webhook_id") if isinstance(payload, dict) else None,
        }
        if actor_id:
            normalized_event["actor_id"] = actor_id
        if actor_id and actor_id in settings.plane_webhook_ignored_actor_id_set():
            log_extra = {
                "correlation_id": correlation_id,
                "plane_delivery_id": x_plane_delivery,
                "plane_event": normalized_event["event"],
                "plane_action": normalized_event["action"],
                "plane_resource_id": normalized_event["resource_id"],
                "plane_webhook_id": normalized_event["webhook_id"],
                "plane_actor_id": actor_id,
                "queued": False,
                "duplicate": False,
                "suppressed": True,
                "suppressed_reason": "ignored_actor",
            }
            logger.info("plane webhook suppressed", extra=log_extra)
            return PlaneWebhookAck(
                accepted=True,
                duplicate=False,
                queued=False,
                suppressed=True,
                suppressed_reason="ignored_actor",
                **normalized_event,
            )
        try:
            queued = FilePlaneWebhookQueue(
                queue_path=settings.plane_webhook_queue_path,
                dedupe_path=settings.plane_webhook_dedupe_path,
            ).enqueue(delivery_id=x_plane_delivery, event=normalized_event)
        except PlaneWebhookQueueError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="plane webhook queue is unavailable",
            ) from exc
        log_extra = {
            "correlation_id": correlation_id,
            "plane_delivery_id": x_plane_delivery,
            "plane_event": normalized_event["event"],
            "plane_action": normalized_event["action"],
            "plane_resource_id": normalized_event["resource_id"],
            "plane_webhook_id": normalized_event["webhook_id"],
            "plane_actor_id": actor_id,
            "queued": queued,
            "duplicate": not queued,
            "suppressed": False,
            "suppressed_reason": None,
        }
        if queued:
            logger.info("plane webhook queued", extra=log_extra)
        else:
            logger.info("plane webhook duplicate suppressed", extra=log_extra)

        return PlaneWebhookAck(
            accepted=True,
            duplicate=not queued,
            queued=queued,
            **normalized_event,
        )

    return router
