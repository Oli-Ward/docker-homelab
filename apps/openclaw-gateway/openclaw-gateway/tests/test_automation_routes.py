import httpx
import pytest

from openclaw_gateway.main import create_app
from openclaw_gateway.schemas.automation import N8nSmokeResponse
from openclaw_gateway.settings import GatewaySettings


def make_settings() -> GatewaySettings:
    return GatewaySettings(
        gateway_auth_token="gateway-secret",
        jellyfin_url="http://jellyfin:8096",
        jellyfin_api_key="jellyfin-secret",
        jellyseerr_url="http://jellyseerr:5055",
        jellyseerr_api_key="jellyseerr-secret",
        sonarr_url="http://sonarr:8989",
        sonarr_api_key="sonarr-secret",
        radarr_url="http://radarr:7878",
        radarr_api_key="radarr-secret",
        n8n_webhook_base_url="http://n8n:5678",
        n8n_openclaw_smoke_path="/webhook/openclaw-smoke",
        upstream_timeout_seconds=5.0,
    )


def make_app():
    return create_app(settings=make_settings())


@pytest.mark.asyncio
async def test_n8n_smoke_route_requires_auth():
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/v1/automation/n8n/openclaw-smoke")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_n8n_smoke_route_returns_static_success_with_request_id(monkeypatch):
    observed_request_ids: list[str] = []

    async def openclaw_smoke(self, request_id: str) -> N8nSmokeResponse:
        observed_request_ids.append(request_id)
        return N8nSmokeResponse(ok=True, workflow="openclaw-smoke", received=True)

    monkeypatch.setattr("openclaw_gateway.routers.automation.N8nClient.openclaw_smoke", openclaw_smoke)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/automation/n8n/openclaw-smoke",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["workflow"] == "openclaw-smoke"
    assert body["received"] is True
    assert body["request_id"] == observed_request_ids[0]
    assert len(observed_request_ids[0]) > 10


@pytest.mark.asyncio
async def test_n8n_smoke_route_echoes_submitted_request_id(monkeypatch):
    observed_request_ids: list[str] = []

    async def openclaw_smoke(self, request_id: str) -> N8nSmokeResponse:
        observed_request_ids.append(request_id)
        return N8nSmokeResponse(ok=True, workflow="openclaw-smoke", received=True)

    monkeypatch.setattr("openclaw_gateway.routers.automation.N8nClient.openclaw_smoke", openclaw_smoke)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/automation/n8n/openclaw-smoke",
            headers={"Authorization": "Bearer gateway-secret"},
            json={"request_id": "openclaw-req-1"},
        )

    assert response.status_code == 200
    assert observed_request_ids == ["openclaw-req-1"]
    assert response.json()["request_id"] == "openclaw-req-1"


@pytest.mark.asyncio
async def test_n8n_smoke_route_maps_timeout_without_secret_leak(monkeypatch):
    async def openclaw_smoke(self, request_id: str) -> N8nSmokeResponse:
        raise httpx.TimeoutException("gateway-secret timeout")

    monkeypatch.setattr("openclaw_gateway.routers.automation.N8nClient.openclaw_smoke", openclaw_smoke)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/automation/n8n/openclaw-smoke",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 504
    assert response.json() == {"detail": "n8n timed out"}


@pytest.mark.asyncio
async def test_n8n_smoke_route_maps_upstream_status_without_secret_leak(monkeypatch):
    async def openclaw_smoke(self, request_id: str) -> N8nSmokeResponse:
        request = httpx.Request("POST", "http://n8n:5678/webhook/openclaw-smoke")
        response = httpx.Response(404, request=request, text="gateway-secret")
        raise httpx.HTTPStatusError("gateway-secret", request=request, response=response)

    monkeypatch.setattr("openclaw_gateway.routers.automation.N8nClient.openclaw_smoke", openclaw_smoke)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/automation/n8n/openclaw-smoke",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "n8n returned 404"}


@pytest.mark.asyncio
async def test_n8n_smoke_route_maps_network_error_without_secret_leak(monkeypatch):
    async def openclaw_smoke(self, request_id: str) -> N8nSmokeResponse:
        raise httpx.ConnectError("gateway-secret connection failed")

    monkeypatch.setattr("openclaw_gateway.routers.automation.N8nClient.openclaw_smoke", openclaw_smoke)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/automation/n8n/openclaw-smoke",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "n8n request failed"}
