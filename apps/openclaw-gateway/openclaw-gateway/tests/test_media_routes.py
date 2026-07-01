import httpx
import pytest

from openclaw_gateway.main import create_app
from openclaw_gateway.schemas.automation import RatingPromptForwardResponse
from openclaw_gateway.schemas.media import (
    JellyseerrRequestResponse,
    MediaItem,
    MediaSearchResponse,
    MovieStatistics,
    MovieSummary,
    MovieSummaryResponse,
    SeriesStatistics,
    SeriesSummary,
    SeriesSummaryResponse,
)
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
        n8n_jellyfin_rating_prompt_path="/webhook/jellyfin-rating-prompt",
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
async def test_jellyfin_watch_completed_route_forwards_movie_prompt(monkeypatch):
    async def forward_rating_prompt(self, event):
        assert event.item_id == "jellyfin-movie-1"
        assert event.title == "Alien"
        assert event.year == 1979
        assert event.watched_at == "2026-07-01T07:10:00Z"
        assert event.user_id == "oli-profile"
        assert event.dedupe_key == "jellyfin-movie-1:2026-07-01T07:10:00Z"
        return RatingPromptForwardResponse(
            ok=True,
            workflow="jellyfin-rating-prompt",
            received=True,
            dedupe_key=event.dedupe_key,
        )

    monkeypatch.setattr(
        "openclaw_gateway.routers.media.N8nClient.forward_rating_prompt",
        forward_rating_prompt,
    )
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/media/jellyfin/watch-completed",
            headers={"Authorization": "Bearer gateway-secret"},
            json={
                "event": "playback.stop",
                "item_id": "jellyfin-movie-1",
                "item_type": "movie",
                "title": "Alien",
                "year": 1979,
                "watched_at": "2026-07-01T07:10:00Z",
                "user_id": "oli-profile",
                "completed": True,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "forwarded",
        "dedupe_key": "jellyfin-movie-1:2026-07-01T07:10:00Z",
        "forwarded": True,
        "message": "Completed movie event forwarded for rating prompt.",
    }


@pytest.mark.asyncio
async def test_jellyfin_watch_completed_route_rejects_non_movies(monkeypatch):
    async def forward_rating_prompt(self, event):
        raise AssertionError("non-movie events must not be forwarded")

    monkeypatch.setattr(
        "openclaw_gateway.routers.media.N8nClient.forward_rating_prompt",
        forward_rating_prompt,
    )
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/media/jellyfin/watch-completed",
            headers={"Authorization": "Bearer gateway-secret"},
            json={
                "event": "playback.stop",
                "item_id": "episode-1",
                "item_type": "episode",
                "title": "Episode One",
                "watched_at": "2026-07-01T07:10:00Z",
                "completed": True,
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_jellyfin_watch_completed_route_rejects_partial_playback(monkeypatch):
    async def forward_rating_prompt(self, event):
        raise AssertionError("partial playback must not be forwarded")

    monkeypatch.setattr(
        "openclaw_gateway.routers.media.N8nClient.forward_rating_prompt",
        forward_rating_prompt,
    )
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/media/jellyfin/watch-completed",
            headers={"Authorization": "Bearer gateway-secret"},
            json={
                "event": "playback.progress",
                "item_id": "jellyfin-movie-1",
                "item_type": "movie",
                "title": "Alien",
                "watched_at": "2026-07-01T07:10:00Z",
                "completed": False,
            },
        )

    assert response.status_code == 422


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
async def test_jellyseerr_request_route_dry_run_validates_without_creating(monkeypatch):
    async def validate_request(self, media_type: str, tmdb_id: int):
        assert media_type == "movie"
        assert tmdb_id == 348
        return JellyseerrRequestResponse(
            status="valid",
            media_type="movie",
            tmdb_id=348,
            message="Request target is valid; no request was created.",
            request_id=None,
            duplicate=False,
            dry_run=True,
        )

    monkeypatch.setattr(
        "openclaw_gateway.routers.media.JellyseerrClient.validate_request",
        validate_request,
    )
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/media/jellyseerr/requests",
            headers={"Authorization": "Bearer gateway-secret"},
            json={
                "media_type": "movie",
                "tmdb_id": 348,
                "note": "requested by OpenClaw",
                "dry_run": True,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "valid",
        "media_type": "movie",
        "tmdb_id": 348,
        "message": "Request target is valid; no request was created.",
        "request_id": None,
        "duplicate": False,
        "dry_run": True,
    }


@pytest.mark.asyncio
async def test_jellyseerr_request_route_requires_auth():
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/media/jellyseerr/requests",
            json={"media_type": "movie", "tmdb_id": 348, "dry_run": True},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_jellyseerr_request_route_creates_when_dry_run_is_false(monkeypatch):
    async def create_request(self, media_type: str, tmdb_id: int):
        assert media_type == "tv"
        assert tmdb_id == 12345
        return JellyseerrRequestResponse(
            status="created",
            media_type="tv",
            tmdb_id=12345,
            message="Jellyseerr request created.",
            request_id=77,
            duplicate=False,
            dry_run=False,
        )

    monkeypatch.setattr(
        "openclaw_gateway.routers.media.JellyseerrClient.create_request",
        create_request,
    )
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/media/jellyseerr/requests",
            headers={"Authorization": "Bearer gateway-secret"},
            json={
                "media_type": "tv",
                "tmdb_id": 12345,
                "note": "approved by Oli",
                "dry_run": False,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "created",
        "media_type": "tv",
        "tmdb_id": 12345,
        "message": "Jellyseerr request created.",
        "request_id": 77,
        "duplicate": False,
        "dry_run": False,
    }


@pytest.mark.asyncio
async def test_sonarr_series_route_requires_auth():
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/media/sonarr/series")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sonarr_series_route_returns_normalized_items(monkeypatch):
    async def series(self) -> SeriesSummaryResponse:
        return SeriesSummaryResponse(
            items=[
                SeriesSummary(
                    id="12",
                    tvdb_id=12345,
                    title="Severance",
                    year=2022,
                    status="continuing",
                    monitored=True,
                    path="/tv/Severance",
                    quality_profile_id=3,
                    statistics=SeriesStatistics(
                        season_count=2,
                        episode_file_count=10,
                        episode_count=19,
                        total_episode_count=19,
                        size_on_disk=123456789,
                    ),
                    tags=[4, 9],
                )
            ]
        )

    monkeypatch.setattr("openclaw_gateway.routers.media.SonarrClient.series", series)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/media/sonarr/series",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "12",
                "tvdb_id": 12345,
                "title": "Severance",
                "year": 2022,
                "status": "continuing",
                "monitored": True,
                "path": "/tv/Severance",
                "quality_profile_id": 3,
                "statistics": {
                    "season_count": 2,
                    "episode_file_count": 10,
                    "episode_count": 19,
                    "total_episode_count": 19,
                    "size_on_disk": 123456789,
                },
                "tags": [4, 9],
            }
        ]
    }


@pytest.mark.asyncio
async def test_radarr_movies_route_requires_auth():
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/media/radarr/movies")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_radarr_movies_route_returns_normalized_items(monkeypatch):
    async def movies(self) -> MovieSummaryResponse:
        return MovieSummaryResponse(
            items=[
                MovieSummary(
                    id="34",
                    tmdb_id=348,
                    title="Alien",
                    year=1979,
                    status="released",
                    monitored=True,
                    has_file=True,
                    available=True,
                    path="/movies/Alien (1979)",
                    quality_profile_id=2,
                    statistics=MovieStatistics(
                        movie_file_count=1,
                        size_on_disk=987654321,
                    ),
                    tags=[7],
                )
            ]
        )

    monkeypatch.setattr("openclaw_gateway.routers.media.RadarrClient.movies", movies)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/media/radarr/movies",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "34",
                "tmdb_id": 348,
                "title": "Alien",
                "year": 1979,
                "status": "released",
                "monitored": True,
                "has_file": True,
                "available": True,
                "path": "/movies/Alien (1979)",
                "quality_profile_id": 2,
                "statistics": {
                    "movie_file_count": 1,
                    "size_on_disk": 987654321,
                },
                "tags": [7],
            }
        ]
    }


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


@pytest.mark.asyncio
async def test_upstream_http_error_maps_to_502(monkeypatch):
    async def search(self, query: str) -> MediaSearchResponse:
        raise httpx.HTTPError("network failed")

    monkeypatch.setattr("openclaw_gateway.routers.media.JellyfinClient.search", search)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/media/jellyfin/search?q=alien",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 502
    assert response.json()["detail"] == "jellyfin request failed"
