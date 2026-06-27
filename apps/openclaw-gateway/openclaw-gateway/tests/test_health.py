import httpx
import pytest

from openclaw_gateway.main import create_app
from openclaw_gateway.settings import GatewaySettings


@pytest.mark.asyncio
async def test_health_is_public():
    settings = GatewaySettings(
        gateway_auth_token="gateway-secret",
        jellyfin_url="http://jellyfin:8096",
        jellyfin_api_key="jellyfin-secret",
        jellyseerr_url="http://jellyseerr:5055",
        jellyseerr_api_key="jellyseerr-secret",
        upstream_timeout_seconds=5.0,
    )
    transport = httpx.ASGITransport(app=create_app(settings=settings))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
