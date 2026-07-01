import httpx
import pytest
from fastapi import Depends, FastAPI

from openclaw_gateway.auth import require_gateway_token
from openclaw_gateway.settings import GatewaySettings


def make_app() -> FastAPI:
    settings = GatewaySettings(
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
        n8n_jellyfin_rating_prompt_path="/webhook/jellyfin-rating-prompt",
        upstream_timeout_seconds=5.0,
    )
    app = FastAPI()

    @app.get("/protected", dependencies=[Depends(require_gateway_token(settings))])
    async def protected() -> dict[str, str]:
        return {"ok": "true"}

    return app


@pytest.mark.asyncio
async def test_missing_bearer_token_is_unauthorized():
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/protected")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"


@pytest.mark.asyncio
async def test_invalid_bearer_token_is_unauthorized():
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/protected",
            headers={"Authorization": "Bearer wrong-token"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid bearer token"


@pytest.mark.asyncio
async def test_valid_bearer_token_is_allowed():
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/protected",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": "true"}
