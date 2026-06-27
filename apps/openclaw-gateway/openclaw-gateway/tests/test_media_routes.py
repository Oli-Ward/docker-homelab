import httpx
import pytest

from openclaw_gateway.main import create_app
from openclaw_gateway.schemas.media import MediaItem, MediaSearchResponse
from openclaw_gateway.settings import GatewaySettings


def make_settings() -> GatewaySettings:
    return GatewaySettings(
        gateway_auth_token="gateway-secret",
        jellyfin_url="http://jellyfin:8096",
        jellyfin_api_key="jellyfin-secret",
        jellyseerr_url="http://jellyseerr:5055",
        jellyseerr_api_key="jellyseerr-secret",
        upstream_timeout_seconds=5.0,
    )


def make_app():
    return create_app(settings=make_settings())


@pytest.mark.asyncio
async def test_media_routes_require_auth():
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/media/jellyfin/search?q=alien")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_jellyfin_search_route_returns_normalized_items(monkeypatch):
    async def search(self, query: str) -> MediaSearchResponse:
        assert query == "alien"
        return MediaSearchResponse(
            items=[
                MediaItem(
                    id="abc",
                    type="movie",
                    title="Alien",
                    year=1979,
                    overview="Space horror",
                    available=True,
                )
            ]
        )

    monkeypatch.setattr("openclaw_gateway.routers.media.JellyfinClient.search", search)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/media/jellyfin/search?q=alien",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "abc",
                "type": "movie",
                "title": "Alien",
                "year": 1979,
                "overview": "Space horror",
                "available": True,
                "request_status": None,
            }
        ]
    }


@pytest.mark.asyncio
async def test_jellyfin_library_route_returns_normalized_items(monkeypatch):
    async def library(self) -> MediaSearchResponse:
        return MediaSearchResponse(
            items=[
                MediaItem(
                    id="series-1",
                    type="series",
                    title="Severance",
                    year=2022,
                    available=True,
                )
            ]
        )

    monkeypatch.setattr("openclaw_gateway.routers.media.JellyfinClient.library", library)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/media/jellyfin/library",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 200
    assert response.json()["items"][0]["title"] == "Severance"
    assert response.json()["items"][0]["type"] == "series"


@pytest.mark.asyncio
async def test_jellyseerr_search_route_returns_normalized_items(monkeypatch):
    async def search(self, query: str) -> MediaSearchResponse:
        assert query == "alien"
        return MediaSearchResponse(
            items=[
                MediaItem(
                    id="348",
                    type="movie",
                    title="Alien",
                    year=1979,
                    overview="Space horror",
                    available=True,
                    request_status="approved",
                )
            ]
        )

    monkeypatch.setattr("openclaw_gateway.routers.media.JellyseerrClient.search", search)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/media/jellyseerr/search?q=alien",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 200
    assert response.json()["items"][0]["request_status"] == "approved"
    assert response.json()["items"][0]["available"] is True


@pytest.mark.asyncio
async def test_upstream_timeout_maps_to_504(monkeypatch):
    async def search(self, query: str) -> MediaSearchResponse:
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("openclaw_gateway.routers.media.JellyfinClient.search", search)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/media/jellyfin/search?q=alien",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 504
    assert response.json()["detail"] == "jellyfin timed out"


@pytest.mark.asyncio
async def test_upstream_http_status_error_maps_to_502(monkeypatch):
    async def search(self, query: str) -> MediaSearchResponse:
        request = httpx.Request("GET", "http://jellyfin:8096/Items")
        response = httpx.Response(500, request=request)
        raise httpx.HTTPStatusError("server error", request=request, response=response)

    monkeypatch.setattr("openclaw_gateway.routers.media.JellyfinClient.search", search)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/media/jellyfin/search?q=alien",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 502
    assert response.json()["detail"] == "jellyfin returned 500"
