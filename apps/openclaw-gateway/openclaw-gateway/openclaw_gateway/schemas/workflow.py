from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

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
    event_type: str | None = None
    schema_version: str | None = None
    raw_payload_hash: str | None = None
    resource_id: str | None = None
    webhook_id: str | None = None
    actor_id: str | None = None
    team: str | None = None
    project_id: str | None = None
    source_identifier: str | None = None
    sequence_id: int | None = None
    name: str | None = None
    state_id: str | None = None
    state_name: str | None = None
    priority: str | int | None = None
    label_names: list[str] | None = None
    agent_ready: dict[str, bool] | None = None
    agent_ready_checks: list[str] | None = None
    queued: bool
    duplicate: bool
    ignored: bool = False
    ignored_reason: str | None = None
    suppressed: bool | None = None
    suppressed_reason: str | None = None


class PlaneWebhookQueueStatusResponse(BaseModel):
    configured: bool
    queue_path: str
    dedupe_path: str
    queued_count: int
    dedupe_count: int
    dispatched_count: int
    pending_count: int
    malformed_count: int
    retry_count: int = 0
    dead_letter_count: int = 0
    last_successful_dispatch_at: Any | None = None
    last_dead_letter_delivery_id: str | None = None
    redis_configured: bool = False
    redis_ready: bool | None = None
    n8n_dispatch_configured: bool = False
    last_delivery_id: str | None = None
    last_correlation_id: str | None = None


class PlaneWebhookDispatchResponse(BaseModel):
    dispatched_count: int
    pending_count: int
    delivery_ids: list[str]
    failed_delivery_id: str | None = None


class PlaneWebhookReplayResponse(BaseModel):
    replayed: bool
    delivery_id: str


class PlaneWritebackClaim(BaseModel):
    claim_id: str | None = Field(default=None, min_length=1)
    source_identifier: str | None = Field(default=None, min_length=1)
    phase: str | None = Field(default=None, min_length=1)
    writeback_phase: str | None = Field(default=None, min_length=1)
    correlation_id: str | None = Field(default=None, min_length=1)

    model_config = ConfigDict(extra="allow")


class PlaneWritebackOperation(BaseModel):
    project_id: str = Field(min_length=1)
    work_item_id: str = Field(min_length=1)
    name: str | None = Field(default=None, min_length=1)
    description_html: str | None = None
    state_id: str | None = None
    priority: Literal["urgent", "high", "medium", "low", "none"] | int | None = None
    label_ids: list[str] | None = None
    assignee_ids: list[str] | None = None
    parent_id: str | None = None
    comment_html: str | None = Field(default=None, min_length=1)

    model_config = ConfigDict(extra="allow")


class PlaneWritebackRequest(BaseModel):
    operation: PlaneWritebackOperation
    claim: PlaneWritebackClaim | None = None
    claim_metadata: PlaneWritebackClaim | None = None
    claim_id: str | None = Field(default=None, min_length=1)
    source_identifier: str | None = Field(default=None, min_length=1)
    phase: str | None = Field(default=None, min_length=1)
    writeback_phase: str | None = Field(default=None, min_length=1)

    model_config = ConfigDict(extra="allow")


class PlaneWritebackResponse(BaseModel):
    ok: bool
    applied: bool
