import hashlib
import hmac
import json
import logging

import httpx
import pytest

from openclaw_gateway.clients.plane import PlaneApiError, PlaneResponseError
from openclaw_gateway.main import create_app
from openclaw_gateway.schemas.workflow import (
    PlaneComment,
    PlaneLabel,
    PlaneLabelsResponse,
    PlaneProject,
    PlaneProjectsResponse,
    PlaneState,
    PlaneStatesResponse,
    PlaneWorkItem,
    PlaneWorkItemsResponse,
)
from openclaw_gateway.settings import GatewaySettings


def make_settings(**overrides) -> GatewaySettings:
    values = {
        "gateway_auth_token": "gateway-secret",
        "jellyfin_url": "http://jellyfin:8096",
        "jellyfin_api_key": "jellyfin-secret",
        "seerr_url": "http://seerr:5055",
        "seerr_api_key": "seerr-secret",
        "sonarr_url": "http://sonarr:8989",
        "sonarr_api_key": "sonarr-secret",
        "radarr_url": "http://radarr:7878",
        "radarr_api_key": "radarr-secret",
        "ryot_url": "http://ryot:8000",
        "ryot_admin_access_token": "ryot-secret",
        "plane_api_base_url": "http://plane:8085",
        "plane_api_key": "plane-secret",
        "plane_workspace_slug": "openclaw",
        "plane_webhook_secret": "plane-webhook-secret",
        "n8n_webhook_base_url": "http://n8n:5678",
        "n8n_openclaw_smoke_path": "/webhook/openclaw-smoke",
        "upstream_timeout_seconds": 5.0,
    }
    values.update(overrides)
    return GatewaySettings(**values)


def make_app(**overrides):
    return create_app(settings=make_settings(**overrides))


def plane_signature(payload: dict) -> str:
    return hmac.new(
        b"plane-webhook-secret",
        msg=json.dumps(payload).encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


@pytest.mark.asyncio
async def test_plane_routes_require_auth():
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/workflow/plane/projects")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_plane_projects_route_returns_projects(monkeypatch):
    async def list_projects(self) -> PlaneProjectsResponse:
        return PlaneProjectsResponse(items=[PlaneProject(id="project-1", name="OpenClaw")])

    monkeypatch.setattr("openclaw_gateway.routers.workflow.PlaneClient.list_projects", list_projects)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/workflow/plane/projects",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 200
    assert response.json()["items"][0]["name"] == "OpenClaw"


@pytest.mark.asyncio
async def test_plane_search_route_passes_query_params(monkeypatch):
    observed: dict[str, object] = {}

    async def search_work_items(
        self,
        query: str,
        project_id: str | None = None,
        limit: int | None = None,
    ) -> PlaneWorkItemsResponse:
        observed.update({"query": query, "project_id": project_id, "limit": limit})
        return PlaneWorkItemsResponse(
            items=[PlaneWorkItem(id="work-item-1", name="Wire Plane adapter", project_id="project-1")]
        )

    monkeypatch.setattr(
        "openclaw_gateway.routers.workflow.PlaneClient.search_work_items",
        search_work_items,
    )
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/workflow/plane/search",
            params={"q": "adapter", "project_id": "project-1", "limit": 5},
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 200
    assert observed == {"query": "adapter", "project_id": "project-1", "limit": 5}
    assert response.json()["items"][0]["id"] == "work-item-1"


@pytest.mark.asyncio
async def test_plane_metadata_routes_return_states_and_labels(monkeypatch):
    async def list_states(self, project_id: str) -> PlaneStatesResponse:
        assert project_id == "project-1"
        return PlaneStatesResponse(items=[PlaneState(id="state-1", name="Ready for Agent")])

    async def list_labels(self, project_id: str) -> PlaneLabelsResponse:
        assert project_id == "project-1"
        return PlaneLabelsResponse(items=[PlaneLabel(id="label-1", name="openclaw")])

    monkeypatch.setattr("openclaw_gateway.routers.workflow.PlaneClient.list_states", list_states)
    monkeypatch.setattr("openclaw_gateway.routers.workflow.PlaneClient.list_labels", list_labels)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        states = await client.get(
            "/v1/workflow/plane/projects/project-1/states",
            headers={"Authorization": "Bearer gateway-secret"},
        )
        labels = await client.get(
            "/v1/workflow/plane/projects/project-1/labels",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert states.status_code == 200
    assert states.json()["items"][0]["name"] == "Ready for Agent"
    assert labels.status_code == 200
    assert labels.json()["items"][0]["name"] == "openclaw"


@pytest.mark.asyncio
async def test_plane_create_update_and_comment_routes(monkeypatch):
    observed: dict[str, object] = {}

    async def create_work_item(self, project_id, work_item):
        observed["create"] = (project_id, work_item.name)
        return PlaneWorkItem(id="work-item-1", name=work_item.name, project_id=project_id)

    async def update_work_item(self, project_id, work_item_id, update):
        observed["update"] = (project_id, work_item_id, update.state_id)
        return PlaneWorkItem(id=work_item_id, name="Updated", project_id=project_id, state_id=update.state_id)

    async def add_comment(self, project_id, work_item_id, comment):
        observed["comment"] = (project_id, work_item_id, comment.comment_html)
        return PlaneComment(id="comment-1", comment_html=comment.comment_html)

    monkeypatch.setattr("openclaw_gateway.routers.workflow.PlaneClient.create_work_item", create_work_item)
    monkeypatch.setattr("openclaw_gateway.routers.workflow.PlaneClient.update_work_item", update_work_item)
    monkeypatch.setattr("openclaw_gateway.routers.workflow.PlaneClient.add_comment", add_comment)
    transport = httpx.ASGITransport(app=make_app())
    headers = {"Authorization": "Bearer gateway-secret"}
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post(
            "/v1/workflow/plane/projects/project-1/work-items",
            headers=headers,
            json={"name": "Created from route"},
        )
        updated = await client.patch(
            "/v1/workflow/plane/projects/project-1/work-items/work-item-1",
            headers=headers,
            json={"state_id": "state-started"},
        )
        commented = await client.post(
            "/v1/workflow/plane/projects/project-1/work-items/work-item-1/comments",
            headers=headers,
            json={"comment_html": "<p>Progress</p>"},
        )

    assert created.status_code == 200
    assert updated.status_code == 200
    assert commented.status_code == 200
    assert observed == {
        "create": ("project-1", "Created from route"),
        "update": ("project-1", "work-item-1", "state-started"),
        "comment": ("project-1", "work-item-1", "<p>Progress</p>"),
    }


@pytest.mark.asyncio
async def test_plane_write_routes_emit_secret_free_audit_logs(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="openclaw_gateway.routers.workflow")

    async def create_work_item(self, project_id, work_item):
        return PlaneWorkItem(id="created-work-item", name=work_item.name, project_id=project_id)

    async def update_work_item(self, project_id, work_item_id, update):
        return PlaneWorkItem(id=work_item_id, name="Updated", project_id=project_id, state_id=update.state_id)

    async def add_comment(self, project_id, work_item_id, comment):
        return PlaneComment(id="comment-1", comment_html=comment.comment_html)

    monkeypatch.setattr("openclaw_gateway.routers.workflow.PlaneClient.create_work_item", create_work_item)
    monkeypatch.setattr("openclaw_gateway.routers.workflow.PlaneClient.update_work_item", update_work_item)
    monkeypatch.setattr("openclaw_gateway.routers.workflow.PlaneClient.add_comment", add_comment)

    transport = httpx.ASGITransport(app=make_app())
    headers = {"Authorization": "Bearer gateway-secret"}
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post(
            "/v1/workflow/plane/projects/project-1/work-items",
            headers=headers,
            json={
                "name": "Created from route",
                "description_html": "<p>contains private implementation context</p>",
            },
        )
        await client.patch(
            "/v1/workflow/plane/projects/project-1/work-items/work-item-1",
            headers=headers,
            json={
                "state_id": "state-started",
                "description_html": "<p>contains update context</p>",
            },
        )
        await client.post(
            "/v1/workflow/plane/projects/project-1/work-items/work-item-1/comments",
            headers=headers,
            json={"comment_html": "<p>Progress with sensitive-ish details</p>"},
        )

    audit_records = [
        record
        for record in caplog.records
        if record.message == "plane workflow write audit"
    ]
    assert [
        {
            "operation": record.operation,
            "project_id": record.project_id,
            "work_item_id": getattr(record, "work_item_id", None),
            "plane_item_id": getattr(record, "plane_item_id", None),
        }
        for record in audit_records
    ] == [
        {
            "operation": "plane_work_item_create",
            "project_id": "project-1",
            "work_item_id": None,
            "plane_item_id": "created-work-item",
        },
        {
            "operation": "plane_work_item_update",
            "project_id": "project-1",
            "work_item_id": "work-item-1",
            "plane_item_id": "work-item-1",
        },
        {
            "operation": "plane_work_item_comment",
            "project_id": "project-1",
            "work_item_id": "work-item-1",
            "plane_item_id": "comment-1",
        },
    ]
    rendered_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "gateway-secret" not in rendered_logs
    assert "plane-secret" not in rendered_logs
    assert "private implementation context" not in rendered_logs
    assert "contains update context" not in rendered_logs
    assert "sensitive-ish details" not in rendered_logs


@pytest.mark.asyncio
async def test_plane_routes_map_invalid_plane_response_to_secret_free_gateway_error(monkeypatch):
    async def list_projects(self) -> PlaneProjectsResponse:
        raise PlaneResponseError("plane returned invalid json response")

    monkeypatch.setattr("openclaw_gateway.routers.workflow.PlaneClient.list_projects", list_projects)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/workflow/plane/projects",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "plane returned an invalid response"}


@pytest.mark.asyncio
async def test_plane_routes_map_plane_api_error_to_secret_free_gateway_error(monkeypatch):
    async def list_projects(self) -> PlaneProjectsResponse:
        raise PlaneApiError(status_code=429, kind="rate_limited")

    monkeypatch.setattr("openclaw_gateway.routers.workflow.PlaneClient.list_projects", list_projects)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/workflow/plane/projects",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "plane returned 429"}


@pytest.mark.asyncio
async def test_plane_webhook_accepts_signed_issue_event_without_gateway_bearer_token(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="openclaw_gateway.routers.workflow")
    queue_path = tmp_path / "plane-webhooks" / "events.jsonl"
    payload = {
        "event": "issue",
        "action": "update",
        "webhook_id": "webhook-1",
        "workspace_id": "workspace-1",
        "data": {"id": "work-item-1", "name": "Ready for agent"},
    }
    transport = httpx.ASGITransport(app=make_app(plane_webhook_queue_path=str(queue_path)))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/workflow/plane/webhook",
            headers={
                "X-Plane-Delivery": "delivery-1",
                "X-Plane-Event": "issue",
                "X-Plane-Signature": plane_signature(payload),
            },
            json=payload,
        )

    assert response.status_code == 200
    assert response.json() == {
        "accepted": True,
        "delivery_id": "delivery-1",
        "event": "issue",
        "action": "update",
        "resource_id": "work-item-1",
        "webhook_id": "webhook-1",
        "correlation_id": "plane:delivery-1",
        "queued": True,
        "duplicate": False,
    }
    [queued_event] = [json.loads(line) for line in queue_path.read_text().splitlines()]
    assert queued_event == {
        "delivery_id": "delivery-1",
        "event": "issue",
        "action": "update",
        "resource_id": "work-item-1",
        "webhook_id": "webhook-1",
        "correlation_id": "plane:delivery-1",
    }
    [log_record] = [
        record
        for record in caplog.records
        if record.message == "plane webhook queued"
    ]
    assert log_record.correlation_id == "plane:delivery-1"
    assert log_record.plane_delivery_id == "delivery-1"
    assert log_record.plane_event == "issue"
    assert log_record.plane_action == "update"
    assert log_record.plane_resource_id == "work-item-1"
    assert log_record.plane_webhook_id == "webhook-1"
    assert log_record.duplicate is False


@pytest.mark.asyncio
async def test_plane_webhook_suppresses_duplicate_delivery(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="openclaw_gateway.routers.workflow")
    queue_path = tmp_path / "events.jsonl"
    payload = {
        "event": "issue",
        "action": "update",
        "webhook_id": "webhook-1",
        "data": {"id": "work-item-1"},
    }
    transport = httpx.ASGITransport(app=make_app(plane_webhook_queue_path=str(queue_path)))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await client.post(
            "/v1/workflow/plane/webhook",
            headers={
                "X-Plane-Delivery": "delivery-1",
                "X-Plane-Event": "issue",
                "X-Plane-Signature": plane_signature(payload),
            },
            json=payload,
        )
        duplicate = await client.post(
            "/v1/workflow/plane/webhook",
            headers={
                "X-Plane-Delivery": "delivery-1",
                "X-Plane-Event": "issue",
                "X-Plane-Signature": plane_signature(payload),
            },
            json=payload,
        )

    assert first.status_code == 200
    assert first.json()["queued"] is True
    assert first.json()["duplicate"] is False
    assert duplicate.status_code == 200
    assert duplicate.json()["queued"] is False
    assert duplicate.json()["duplicate"] is True
    assert len(queue_path.read_text().splitlines()) == 1
    duplicate_logs = [
        record
        for record in caplog.records
        if record.message == "plane webhook duplicate suppressed"
    ]
    assert len(duplicate_logs) == 1
    assert duplicate_logs[0].correlation_id == "plane:delivery-1"
    assert duplicate_logs[0].duplicate is True


@pytest.mark.asyncio
async def test_plane_webhook_suppresses_ignored_actor_without_queueing(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="openclaw_gateway.routers.workflow")
    queue_path = tmp_path / "events.jsonl"
    payload = {
        "event": "issue",
        "action": "update",
        "webhook_id": "webhook-1",
        "actor": {"id": "automation-user-1", "display_name": "OpenClaw Bot"},
        "data": {"id": "work-item-1"},
    }
    transport = httpx.ASGITransport(
        app=make_app(
            plane_webhook_queue_path=str(queue_path),
            plane_webhook_ignored_actor_ids="automation-user-1,codex-user-1",
        )
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/workflow/plane/webhook",
            headers={
                "X-Plane-Delivery": "delivery-1",
                "X-Plane-Event": "issue",
                "X-Plane-Signature": plane_signature(payload),
            },
            json=payload,
        )

    assert response.status_code == 200
    assert response.json() == {
        "accepted": True,
        "correlation_id": "plane:delivery-1",
        "delivery_id": "delivery-1",
        "event": "issue",
        "action": "update",
        "resource_id": "work-item-1",
        "webhook_id": "webhook-1",
        "actor_id": "automation-user-1",
        "queued": False,
        "duplicate": False,
        "suppressed": True,
        "suppressed_reason": "ignored_actor",
    }
    assert not queue_path.exists()
    [suppressed_log] = [
        record
        for record in caplog.records
        if record.message == "plane webhook suppressed"
    ]
    assert suppressed_log.correlation_id == "plane:delivery-1"
    assert suppressed_log.plane_actor_id == "automation-user-1"
    assert suppressed_log.suppressed_reason == "ignored_actor"


@pytest.mark.asyncio
async def test_plane_webhook_queue_status_requires_auth(tmp_path):
    queue_path = tmp_path / "events.jsonl"
    transport = httpx.ASGITransport(app=make_app(plane_webhook_queue_path=str(queue_path)))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/workflow/plane/webhook/queue")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_plane_webhook_queue_status_reports_counts(tmp_path):
    queue_path = tmp_path / "events.jsonl"
    transport = httpx.ASGITransport(app=make_app(plane_webhook_queue_path=str(queue_path)))
    payload_1 = {
        "event": "issue",
        "action": "create",
        "webhook_id": "webhook-1",
        "data": {"id": "work-item-1"},
    }
    payload_2 = {
        "event": "issue",
        "action": "update",
        "webhook_id": "webhook-1",
        "data": {"id": "work-item-2"},
    }
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        for delivery_id, payload in (
            ("delivery-1", payload_1),
            ("delivery-2", payload_2),
            ("delivery-1", payload_1),
        ):
            await client.post(
                "/v1/workflow/plane/webhook",
                headers={
                    "X-Plane-Delivery": delivery_id,
                    "X-Plane-Event": "issue",
                    "X-Plane-Signature": plane_signature(payload),
                },
                json=payload,
            )
        response = await client.get(
            "/v1/workflow/plane/webhook/queue",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "configured": True,
        "queue_path": str(queue_path),
        "dedupe_path": f"{queue_path}.seen",
        "queued_count": 2,
        "dedupe_count": 2,
        "malformed_count": 0,
        "last_delivery_id": "delivery-2",
        "last_correlation_id": "plane:delivery-2",
    }


@pytest.mark.asyncio
async def test_plane_webhook_queue_status_reports_empty_missing_queue(tmp_path):
    queue_path = tmp_path / "missing" / "events.jsonl"
    transport = httpx.ASGITransport(app=make_app(plane_webhook_queue_path=str(queue_path)))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/workflow/plane/webhook/queue",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "configured": True,
        "queue_path": str(queue_path),
        "dedupe_path": f"{queue_path}.seen",
        "queued_count": 0,
        "dedupe_count": 0,
        "malformed_count": 0,
        "last_delivery_id": None,
        "last_correlation_id": None,
    }


@pytest.mark.asyncio
async def test_plane_webhook_dispatch_forwards_pending_events_once(tmp_path, monkeypatch):
    queue_path = tmp_path / "events.jsonl"
    forwarded: list[dict[str, object]] = []

    async def forward_plane_webhook_event(self, event: dict[str, object]) -> dict[str, object]:
        forwarded.append(event)
        return {"ok": True, "received": True, "correlation_id": event["correlation_id"]}

    monkeypatch.setattr(
        "openclaw_gateway.routers.workflow.N8nClient.forward_plane_webhook_event",
        forward_plane_webhook_event,
    )
    transport = httpx.ASGITransport(app=make_app(plane_webhook_queue_path=str(queue_path)))
    payloads = [
        {
            "event": "issue",
            "action": "create",
            "webhook_id": "webhook-1",
            "data": {"id": "work-item-1"},
        },
        {
            "event": "issue",
            "action": "update",
            "webhook_id": "webhook-1",
            "data": {"id": "work-item-2"},
        },
    ]
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        for index, payload in enumerate(payloads, start=1):
            await client.post(
                "/v1/workflow/plane/webhook",
                headers={
                    "X-Plane-Delivery": f"delivery-{index}",
                    "X-Plane-Event": "issue",
                    "X-Plane-Signature": plane_signature(payload),
                },
                json=payload,
            )
        first_dispatch = await client.post(
            "/v1/workflow/plane/webhook/dispatch",
            headers={"Authorization": "Bearer gateway-secret"},
        )
        second_dispatch = await client.post(
            "/v1/workflow/plane/webhook/dispatch",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert first_dispatch.status_code == 200
    assert first_dispatch.json() == {
        "dispatched_count": 2,
        "pending_count": 0,
        "delivery_ids": ["delivery-1", "delivery-2"],
        "failed_delivery_id": None,
    }
    assert second_dispatch.status_code == 200
    assert second_dispatch.json() == {
        "dispatched_count": 0,
        "pending_count": 0,
        "delivery_ids": [],
        "failed_delivery_id": None,
    }
    assert [event["delivery_id"] for event in forwarded] == ["delivery-1", "delivery-2"]


@pytest.mark.asyncio
async def test_plane_webhook_dispatch_leaves_failed_delivery_pending_for_retry(tmp_path, monkeypatch):
    queue_path = tmp_path / "events.jsonl"
    attempts: list[str] = []

    async def failing_then_successful_dispatch(self, event: dict[str, object]) -> dict[str, object]:
        attempts.append(str(event["delivery_id"]))
        if len(attempts) == 1:
            raise httpx.ConnectError("n8n unavailable")
        return {"ok": True, "received": True, "correlation_id": event["correlation_id"]}

    monkeypatch.setattr(
        "openclaw_gateway.routers.workflow.N8nClient.forward_plane_webhook_event",
        failing_then_successful_dispatch,
    )
    transport = httpx.ASGITransport(app=make_app(plane_webhook_queue_path=str(queue_path)))
    payload = {
        "event": "issue",
        "action": "update",
        "webhook_id": "webhook-1",
        "data": {"id": "work-item-1"},
    }
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post(
            "/v1/workflow/plane/webhook",
            headers={
                "X-Plane-Delivery": "delivery-1",
                "X-Plane-Event": "issue",
                "X-Plane-Signature": plane_signature(payload),
            },
            json=payload,
        )
        failed_dispatch = await client.post(
            "/v1/workflow/plane/webhook/dispatch",
            headers={"Authorization": "Bearer gateway-secret"},
        )
        retried_dispatch = await client.post(
            "/v1/workflow/plane/webhook/dispatch",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert failed_dispatch.status_code == 502
    assert failed_dispatch.json() == {
        "detail": "plane webhook dispatch failed for delivery-1",
    }
    assert retried_dispatch.status_code == 200
    assert retried_dispatch.json() == {
        "dispatched_count": 1,
        "pending_count": 0,
        "delivery_ids": ["delivery-1"],
        "failed_delivery_id": None,
    }
    assert attempts == ["delivery-1", "delivery-1"]


@pytest.mark.asyncio
async def test_plane_webhook_rejects_invalid_signature():
    payload = {"event": "issue", "action": "update", "data": {"id": "work-item-1"}}
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/workflow/plane/webhook",
            headers={
                "X-Plane-Delivery": "delivery-1",
                "X-Plane-Event": "issue",
                "X-Plane-Signature": "bad-signature",
            },
            json=payload,
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "invalid plane signature"}


@pytest.mark.asyncio
async def test_plane_webhook_requires_configured_secret():
    settings = make_settings()
    settings.plane_webhook_secret = None
    transport = httpx.ASGITransport(app=create_app(settings=settings))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/workflow/plane/webhook",
            headers={
                "X-Plane-Delivery": "delivery-1",
                "X-Plane-Event": "issue",
                "X-Plane-Signature": "bad-signature",
            },
            json={"event": "issue", "action": "update"},
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "plane webhook secret is not configured"}


@pytest.mark.asyncio
async def test_plane_webhook_rejects_missing_delivery_header():
    payload = {"event": "issue", "action": "update"}
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/workflow/plane/webhook",
            headers={
                "X-Plane-Event": "issue",
                "X-Plane-Signature": plane_signature(payload),
            },
            json=payload,
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "missing plane delivery id"}


@pytest.mark.asyncio
async def test_plane_webhook_rejects_malformed_json():
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/workflow/plane/webhook",
            headers={
                "X-Plane-Delivery": "delivery-1",
                "X-Plane-Event": "issue",
                "X-Plane-Signature": "signature",
                "Content-Type": "application/json",
            },
            content=b"{not-json",
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid plane webhook json"}
