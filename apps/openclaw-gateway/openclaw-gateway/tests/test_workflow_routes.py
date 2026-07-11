import hashlib
import hmac
import json

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


def make_settings() -> GatewaySettings:
    return GatewaySettings(
        gateway_auth_token="gateway-secret",
        jellyfin_url="http://jellyfin:8096",
        jellyfin_api_key="jellyfin-secret",
        seerr_url="http://seerr:5055",
        seerr_api_key="seerr-secret",
        sonarr_url="http://sonarr:8989",
        sonarr_api_key="sonarr-secret",
        radarr_url="http://radarr:7878",
        radarr_api_key="radarr-secret",
        ryot_url="http://ryot:8000",
        ryot_admin_access_token="ryot-secret",
        plane_api_base_url="http://plane:8085",
        plane_api_key="plane-secret",
        plane_workspace_slug="openclaw",
        plane_webhook_secret="plane-webhook-secret",
        n8n_webhook_base_url="http://n8n:5678",
        n8n_openclaw_smoke_path="/webhook/openclaw-smoke",
        upstream_timeout_seconds=5.0,
    )


def make_app():
    return create_app(settings=make_settings())


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
async def test_plane_webhook_accepts_signed_issue_event_without_gateway_bearer_token():
    payload = {
        "event": "issue",
        "action": "update",
        "webhook_id": "webhook-1",
        "workspace_id": "workspace-1",
        "data": {"id": "work-item-1", "name": "Ready for agent"},
    }
    transport = httpx.ASGITransport(app=make_app())
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
    }


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
