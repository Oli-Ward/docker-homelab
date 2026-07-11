from typing import Any

from pydantic import BaseModel, Field

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
    PlaneWorkItemLabel,
    PlaneWorkItemsResponse,
    PlaneWorkItemUpdate,
)


class PlaneWebhookAck(BaseModel):
    accepted: bool
    correlation_id: str
    delivery_id: str
    event: str | None = None
    action: str | None = None
    resource_id: str | None = None
    webhook_id: str | None = None
    actor_id: str | None = None
    queued: bool
    duplicate: bool
    suppressed: bool | None = None
    suppressed_reason: str | None = None


class PlaneWebhookQueueStatusResponse(BaseModel):
    configured: bool
    queue_path: str
    dedupe_path: str
    queued_count: int
    dedupe_count: int
    malformed_count: int
    last_delivery_id: str | None = None
    last_correlation_id: str | None = None


class PlaneWebhookDispatchResponse(BaseModel):
    dispatched_count: int
    pending_count: int
    delivery_ids: list[str]
    failed_delivery_id: str | None = None
