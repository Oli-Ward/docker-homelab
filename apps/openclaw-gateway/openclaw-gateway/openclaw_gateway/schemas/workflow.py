from typing import Any, Literal

from pydantic import BaseModel, Field


class PlaneProject(BaseModel):
    id: str
    name: str
    identifier: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class PlaneProjectsResponse(BaseModel):
    items: list[PlaneProject]


class PlaneState(BaseModel):
    id: str
    name: str
    group: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class PlaneStatesResponse(BaseModel):
    items: list[PlaneState]


class PlaneLabel(BaseModel):
    id: str
    name: str
    color: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class PlaneLabelsResponse(BaseModel):
    items: list[PlaneLabel]


class PlaneWorkItemLabel(BaseModel):
    id: str | None = None
    name: str


class PlaneWorkItem(BaseModel):
    id: str
    name: str
    project_id: str | None = None
    sequence_id: int | None = None
    state_id: str | None = None
    priority: str | int | None = None
    labels: list[PlaneWorkItemLabel] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class PlaneWorkItemsResponse(BaseModel):
    items: list[PlaneWorkItem]


class PlaneWorkItemCreate(BaseModel):
    name: str = Field(min_length=1)
    description_html: str | None = None
    state_id: str | None = None
    priority: Literal["urgent", "high", "medium", "low", "none"] | int | None = None
    label_ids: list[str] = Field(default_factory=list)
    assignee_ids: list[str] = Field(default_factory=list)
    parent_id: str | None = None


class PlaneWorkItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description_html: str | None = None
    state_id: str | None = None
    priority: Literal["urgent", "high", "medium", "low", "none"] | int | None = None
    label_ids: list[str] | None = None
    assignee_ids: list[str] | None = None
    parent_id: str | None = None


class PlaneCommentCreate(BaseModel):
    comment_html: str = Field(min_length=1)


class PlaneComment(BaseModel):
    id: str
    comment_html: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class PlaneWebhookAck(BaseModel):
    accepted: bool
    delivery_id: str
    event: str | None = None
    action: str | None = None
    resource_id: str | None = None
    webhook_id: str | None = None
    queued: bool
    duplicate: bool
