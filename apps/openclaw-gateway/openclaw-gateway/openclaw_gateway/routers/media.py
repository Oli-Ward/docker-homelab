from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from openclaw_gateway.auth import require_gateway_token
from openclaw_gateway.clients.jellyfin import JellyfinClient
from openclaw_gateway.clients.jellyseerr import JellyseerrClient
from openclaw_gateway.clients.n8n import N8nClient
from openclaw_gateway.clients.radarr import RadarrClient
from openclaw_gateway.clients.sonarr import SonarrClient
from openclaw_gateway.schemas.media import (
    JellyfinWatchCompletedEvent,
    JellyfinWatchCompletedResponse,
    JellyseerrRequestCreate,
    JellyseerrRequestResponse,
    MediaSearchResponse,
    MovieSummaryResponse,
    SeriesSummaryResponse,
)
from openclaw_gateway.settings import GatewaySettings


ResponseT = TypeVar("ResponseT")


async def _map_upstream_errors(
    upstream_name: str,
    request: Callable[[], Awaitable[ResponseT]],
) -> ResponseT:
    try:
        return await request()
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"{upstream_name} timed out",
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{upstream_name} returned {exc.response.status_code}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{upstream_name} request failed",
        ) from exc


def build_media_router(settings: GatewaySettings) -> APIRouter:
    router = APIRouter(
        prefix="/v1/media",
        dependencies=[Depends(require_gateway_token(settings))],
    )

    def jellyfin_client() -> JellyfinClient:
        return JellyfinClient(
            base_url=str(settings.jellyfin_url),
            api_key=settings.jellyfin_api_key,
            timeout_seconds=settings.upstream_timeout_seconds,
        )

    def jellyseerr_client() -> JellyseerrClient:
        return JellyseerrClient(
            base_url=str(settings.jellyseerr_url),
            api_key=settings.jellyseerr_api_key,
            timeout_seconds=settings.upstream_timeout_seconds,
        )

    def n8n_client() -> N8nClient:
        return N8nClient(
            base_url=str(settings.n8n_webhook_base_url),
            rating_prompt_path=settings.n8n_jellyfin_rating_prompt_path,
            timeout_seconds=settings.upstream_timeout_seconds,
        )

    def sonarr_client() -> SonarrClient:
        return SonarrClient(
            base_url=str(settings.sonarr_url),
            api_key=settings.sonarr_api_key,
            timeout_seconds=settings.upstream_timeout_seconds,
        )

    def radarr_client() -> RadarrClient:
        return RadarrClient(
            base_url=str(settings.radarr_url),
            api_key=settings.radarr_api_key,
            timeout_seconds=settings.upstream_timeout_seconds,
        )

    @router.get("/jellyfin/library")
    async def jellyfin_library() -> MediaSearchResponse:
        return await _map_upstream_errors("jellyfin", jellyfin_client().library)

    @router.get("/jellyfin/search")
    async def jellyfin_search(q: str) -> MediaSearchResponse:
        return await _map_upstream_errors("jellyfin", lambda: jellyfin_client().search(q))

    @router.post("/jellyfin/watch-completed")
    async def jellyfin_watch_completed(
        event: JellyfinWatchCompletedEvent,
    ) -> JellyfinWatchCompletedResponse:
        await _map_upstream_errors(
            "n8n",
            lambda: n8n_client().forward_rating_prompt(event),
        )
        return JellyfinWatchCompletedResponse(
            status="forwarded",
            dedupe_key=event.dedupe_key,
            forwarded=True,
            message="Completed movie event forwarded for rating prompt.",
        )

    @router.get("/jellyseerr/search")
    async def jellyseerr_search(q: str) -> MediaSearchResponse:
        return await _map_upstream_errors("jellyseerr", lambda: jellyseerr_client().search(q))

    @router.post("/jellyseerr/requests")
    async def jellyseerr_request(
        request: JellyseerrRequestCreate,
    ) -> JellyseerrRequestResponse:
        if request.dry_run:
            return await _map_upstream_errors(
                "jellyseerr",
                lambda: jellyseerr_client().validate_request(
                    media_type=request.media_type,
                    tmdb_id=request.tmdb_id,
                ),
            )

        return await _map_upstream_errors(
            "jellyseerr",
            lambda: jellyseerr_client().create_request(
                media_type=request.media_type,
                tmdb_id=request.tmdb_id,
            ),
        )

    @router.get("/sonarr/series")
    async def sonarr_series() -> SeriesSummaryResponse:
        return await _map_upstream_errors("sonarr", sonarr_client().series)

    @router.get("/radarr/movies")
    async def radarr_movies() -> MovieSummaryResponse:
        return await _map_upstream_errors("radarr", radarr_client().movies)

    return router
