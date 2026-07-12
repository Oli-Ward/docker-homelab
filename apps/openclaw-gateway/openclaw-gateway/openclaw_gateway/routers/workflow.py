from collections.abc import Awaitable, Callable
import hashlib
import hmac
import json
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import TypeVar

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from openclaw_gateway.auth import require_gateway_token
from openclaw_gateway.clients.n8n import N8nClient
from openclaw_gateway.plane_webhooks import (
    FilePlaneWebhookQueue,
    PlaneWebhookFailure,
    PlaneWebhookQueue,
    PlaneWebhookQueueError,
    RedisPlaneWebhookQueue,
    classify_plane_event,
    normalize_plane_webhook_event,
)
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
    PlaneWebhookReplayResponse,
)
from openclaw_gateway.settings import GatewaySettings
from openclaw_plane_sdk import PlaneApiError, PlaneClient, PlaneResponseError


ResponseT = TypeVar("ResponseT")
logger = logging.getLogger(__name__)
PLANE_LIST_RESPONSE_EXCLUDE = {"items": {"__all__": {"raw"}}}
PLANE_OBJECT_RESPONSE_EXCLUDE = {"raw"}


def _audit_plane_write(
    *,
    operation: str,
    project_id: str,
    work_item_id: str | None = None,
    plane_item_id: str | None = None,
) -> None:
    logger.info(
        "plane workflow write audit",
        extra={
            "operation": operation,
            "project_id": project_id,
            "work_item_id": work_item_id,
            "plane_item_id": plane_item_id,
        },
    )


def _plane_webhook_queue(settings: GatewaySettings) -> PlaneWebhookQueue:
    if settings.plane_webhook_queue_backend == "file":
        return FilePlaneWebhookQueue(
            queue_path=settings.plane_webhook_queue_path,
            dedupe_path=settings.plane_webhook_dedupe_path,
        )
    try:
        from redis import Redis
    except ImportError as exc:
        raise PlaneWebhookQueueError("redis dependency is unavailable") from exc
    return RedisPlaneWebhookQueue(
        Redis.from_url(settings.plane_webhook_redis_url, decode_responses=True),
        prefix=settings.plane_webhook_redis_prefix,
    )


def _dispatch_failure_type(result: object) -> str | None:
    if isinstance(result, dict):
        if result.get("ok") is False:
            failure_type = result.get("failure_type")
            return failure_type if failure_type in {"retryable", "permanent"} else "retryable"
        return None
    ok = getattr(result, "ok", True)
    if ok is False:
        failure_type = getattr(result, "failure_type", None)
        return failure_type if failure_type in {"retryable", "permanent"} else "retryable"
    return None


def _dispatch_failure_message(result: object, fallback: str) -> str:
    if isinstance(result, dict):
        return str(result.get("detail") or result.get("error_code") or fallback)
    return str(getattr(result, "detail", None) or getattr(result, "error_code", None) or fallback)


def _retry_after(settings: GatewaySettings, attempt: int) -> datetime:
    delay = min(
        settings.plane_webhook_retry_base_seconds * (2 ** max(attempt - 1, 0)),
        settings.plane_webhook_retry_max_seconds,
    )
    jitter = random.uniform(0, delay * 0.2)
    return datetime.now(timezone.utc) + timedelta(seconds=delay + jitter)


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


def _string_value(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _int_value(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _label_names(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    names: list[str] = []
    for label in value:
        if isinstance(label, str) and label:
            names.append(label)
        elif isinstance(label, dict):
            name = _string_value(label.get("name"))
            if name:
                names.append(name)
    return names or None


def _extract_safe_work_item_metadata(data: object) -> dict[str, object]:
    if not isinstance(data, dict):
        return {}

    metadata: dict[str, object] = {}
    for source_key, target_key in (
        ("project_id", "project_id"),
        ("project", "project_id"),
        ("team", "team"),
        ("team_name", "team"),
        ("teamName", "team"),
        ("source_identifier", "source_identifier"),
        ("sourceIdentifier", "source_identifier"),
        ("name", "name"),
        ("state_id", "state_id"),
        ("state", "state_id"),
        ("priority", "priority"),
    ):
        value = _string_value(data.get(source_key))
        if value and target_key not in metadata:
            metadata[target_key] = value

    sequence_id = _int_value(data.get("sequence_id"))
    if sequence_id is not None:
        metadata["sequence_id"] = sequence_id

    state = data.get("state")
    if isinstance(state, dict):
        state_id = _string_value(state.get("id"))
        state_name = _string_value(state.get("name"))
        if state_id:
            metadata["state_id"] = state_id
        if state_name:
            metadata["state_name"] = state_name

    names = _label_names(data.get("labels") or data.get("label_details"))
    if names:
        metadata["label_names"] = names

    return metadata


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

    @router.get(
        "/plane/projects",
        response_model_exclude=PLANE_LIST_RESPONSE_EXCLUDE,
    )
    async def plane_projects() -> PlaneProjectsResponse:
        return await _map_plane_errors(plane_client().list_projects)

    @router.get(
        "/plane/projects/{project_id}/states",
        response_model_exclude=PLANE_LIST_RESPONSE_EXCLUDE,
    )
    async def plane_states(project_id: str) -> PlaneStatesResponse:
        return await _map_plane_errors(lambda: plane_client().list_states(project_id))

    @router.get(
        "/plane/projects/{project_id}/labels",
        response_model_exclude=PLANE_LIST_RESPONSE_EXCLUDE,
    )
    async def plane_labels(project_id: str) -> PlaneLabelsResponse:
        return await _map_plane_errors(lambda: plane_client().list_labels(project_id))

    @router.get(
        "/plane/search",
        response_model_exclude=PLANE_LIST_RESPONSE_EXCLUDE,
    )
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

    @router.get(
        "/plane/projects/{project_id}/work-items",
        response_model_exclude=PLANE_LIST_RESPONSE_EXCLUDE,
    )
    async def plane_project_work_items(
        project_id: str,
        limit: int | None = Query(default=None, ge=1, le=100),
    ) -> PlaneWorkItemsResponse:
        return await _map_plane_errors(
            lambda: plane_client().list_project_work_items(project_id=project_id, limit=limit)
        )

    @router.get(
        "/plane/projects/{project_id}/work-items/{work_item_id}",
        response_model_exclude=PLANE_OBJECT_RESPONSE_EXCLUDE,
    )
    async def plane_work_item(project_id: str, work_item_id: str) -> PlaneWorkItem:
        return await _map_plane_errors(
            lambda: plane_client().get_work_item(project_id=project_id, work_item_id=work_item_id)
        )

    @router.post(
        "/plane/projects/{project_id}/work-items",
        response_model_exclude=PLANE_OBJECT_RESPONSE_EXCLUDE,
    )
    async def plane_create_work_item(
        project_id: str,
        work_item: PlaneWorkItemCreate,
    ) -> PlaneWorkItem:
        created = await _map_plane_errors(
            lambda: plane_client().create_work_item(project_id=project_id, work_item=work_item)
        )
        _audit_plane_write(
            operation="plane_work_item_create",
            project_id=project_id,
            plane_item_id=created.id,
        )
        return created

    @router.patch(
        "/plane/projects/{project_id}/work-items/{work_item_id}",
        response_model_exclude=PLANE_OBJECT_RESPONSE_EXCLUDE,
    )
    async def plane_update_work_item(
        project_id: str,
        work_item_id: str,
        update: PlaneWorkItemUpdate,
    ) -> PlaneWorkItem:
        updated = await _map_plane_errors(
            lambda: plane_client().update_work_item(
                project_id=project_id,
                work_item_id=work_item_id,
                update=update,
            )
        )
        _audit_plane_write(
            operation="plane_work_item_update",
            project_id=project_id,
            work_item_id=work_item_id,
            plane_item_id=updated.id,
        )
        return updated

    @router.post(
        "/plane/projects/{project_id}/work-items/{work_item_id}/comments",
        response_model_exclude=PLANE_OBJECT_RESPONSE_EXCLUDE,
    )
    async def plane_add_comment(
        project_id: str,
        work_item_id: str,
        comment: PlaneCommentCreate,
    ) -> PlaneComment:
        created = await _map_plane_errors(
            lambda: plane_client().add_comment(
                project_id=project_id,
                work_item_id=work_item_id,
                comment=comment,
            )
        )
        _audit_plane_write(
            operation="plane_work_item_comment",
            project_id=project_id,
            work_item_id=work_item_id,
            plane_item_id=created.id,
        )
        return created

    @router.get("/plane/webhook/queue")
    async def plane_webhook_queue_status() -> PlaneWebhookQueueStatusResponse:
        try:
            queue_status = _plane_webhook_queue(settings).status(
                configured=bool(settings.plane_webhook_secret),
                n8n_dispatch_configured=bool(settings.n8n_plane_webhook_dispatch_path),
            )
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
        queue = _plane_webhook_queue(settings)
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
            attempt = int(event.get("retry_attempt", 0) or 0) + 1
            try:
                dispatch_result = await n8n_client().forward_plane_webhook_event(event)
                failure_type = _dispatch_failure_type(dispatch_result)
                if failure_type == "permanent":
                    queue.mark_failed(
                        delivery_id,
                        PlaneWebhookFailure(
                            category="permanent",
                            message=_dispatch_failure_message(dispatch_result, "permanent dispatch failure"),
                        ),
                    )
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"plane webhook dispatch permanent failure for {delivery_id}",
                    )
                if failure_type == "retryable":
                    category = "permanent" if attempt >= settings.plane_webhook_max_attempts else "retryable"
                    queue.mark_failed(
                        delivery_id,
                        PlaneWebhookFailure(
                            category=category,
                            message=_dispatch_failure_message(dispatch_result, "retryable dispatch failure"),
                            retry_after=_retry_after(settings, attempt) if category == "retryable" else None,
                        ),
                    )
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"plane webhook dispatch failed for {delivery_id}",
                    )
                queue.mark_dispatched(delivery_id)
            except PlaneWebhookQueueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="plane webhook queue is unavailable",
                ) from exc
            except httpx.TimeoutException as exc:
                queue.mark_failed(
                    delivery_id,
                    PlaneWebhookFailure(
                        category="retryable",
                        message="n8n dispatch timed out",
                        retry_after=_retry_after(settings, attempt),
                    ),
                )
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"plane webhook dispatch timed out for {delivery_id}",
                ) from exc
            except httpx.HTTPStatusError as exc:
                category = "retryable" if exc.response.status_code >= 500 else "permanent"
                queue.mark_failed(
                    delivery_id,
                    PlaneWebhookFailure(
                        category=category,
                        message=f"n8n returned {exc.response.status_code}",
                        retry_after=_retry_after(settings, attempt) if category == "retryable" else None,
                    ),
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"plane webhook dispatch returned {exc.response.status_code} for {delivery_id}",
                ) from exc
            except httpx.HTTPError as exc:
                queue.mark_failed(
                    delivery_id,
                    PlaneWebhookFailure(
                        category="retryable",
                        message="n8n dispatch failed",
                        retry_after=_retry_after(settings, attempt),
                    ),
                )
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

    @router.post("/plane/webhook/replay")
    async def plane_webhook_replay(
        delivery_id: str = Query(min_length=1),
    ) -> PlaneWebhookReplayResponse:
        try:
            replayed_event = _plane_webhook_queue(settings).replay_dead_letter(delivery_id)
        except PlaneWebhookQueueError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="plane webhook queue is unavailable",
            ) from exc
        if replayed_event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="plane webhook dead-letter delivery was not found",
            )
        return PlaneWebhookReplayResponse(replayed=True, delivery_id=delivery_id)

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
            raw_body = await request.body()
            payload = json.loads(raw_body)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid plane webhook json",
            ) from exc
        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid plane webhook json",
            )

        expected_signature = hmac.new(
            settings.plane_webhook_secret.encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_signature, x_plane_signature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="invalid plane signature",
            )

        normalized_event = normalize_plane_webhook_event(
            payload,
            delivery_id=x_plane_delivery,
            raw_body=raw_body,
            received_at=datetime.now(timezone.utc),
        )
        classification = classify_plane_event(payload)
        correlation_id = str(normalized_event["correlation_id"])
        actor_id = _extract_plane_actor_id(payload)
        if not classification.supported:
            logger.info(
                "plane webhook ignored",
                extra={
                    "correlation_id": correlation_id,
                    "plane_delivery_id": x_plane_delivery,
                    "plane_event": normalized_event["event"],
                    "plane_action": normalized_event["action"],
                    "plane_resource_id": normalized_event["resource_id"],
                    "plane_webhook_id": normalized_event["webhook_id"],
                    "ignored": True,
                    "ignored_reason": classification.ignored_reason,
                },
            )
            return PlaneWebhookAck(
                accepted=True,
                duplicate=False,
                queued=False,
                ignored=True,
                ignored_reason=classification.ignored_reason,
                **normalized_event,
            )
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
                ignored=False,
                suppressed=True,
                suppressed_reason="ignored_actor",
                **normalized_event,
            )
        try:
            enqueue_result = _plane_webhook_queue(settings).enqueue(normalized_event)
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
            "queued": enqueue_result.queued,
            "duplicate": enqueue_result.duplicate,
            "suppressed": False,
            "suppressed_reason": None,
        }
        if enqueue_result.queued:
            logger.info("plane webhook queued", extra=log_extra)
        else:
            logger.info("plane webhook duplicate suppressed", extra=log_extra)

        return PlaneWebhookAck(
            accepted=True,
            duplicate=enqueue_result.duplicate,
            queued=enqueue_result.queued,
            ignored=False,
            **normalized_event,
        )

    return router
