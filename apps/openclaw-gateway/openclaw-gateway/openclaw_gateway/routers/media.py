from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from openclaw_gateway.auth import require_gateway_token
from openclaw_gateway.clients.jellyfin import JellyfinClient
from openclaw_gateway.clients.seerr import SeerrClient
from openclaw_gateway.clients.n8n import N8nClient
from openclaw_gateway.clients.radarr import RadarrClient
from openclaw_gateway.clients.ryot import RyotClient, RyotGraphQLError
from openclaw_gateway.clients.sonarr import SonarrClient
from openclaw_gateway.schemas.media import (
    JellyfinWatchCompletedEvent,
    JellyfinWatchCompletedResponse,
    SeerrRequestCreate,
    SeerrRequestResponse,
    MediaSearchResponse,
    MovieSummaryResponse,
    RyotProbeResponse,
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
    except RyotGraphQLError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{upstream_name} graphql error",
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

    def seerr_client() -> SeerrClient:
        return SeerrClient(
            base_url=str(settings.seerr_url),
            api_key=settings.seerr_api_key,
            timeout_seconds=settings.upstream_timeout_seconds,
        )

    def n8n_client() -> N8nClient:
        return N8nClient(
            base_url=str(settings.n8n_webhook_base_url),
            smoke_path=settings.n8n_openclaw_smoke_path,
            rating_prompt_path=settings.n8n_jellyfin_rating_prompt_path,
            plane_dispatch_path=settings.n8n_plane_webhook_dispatch_path,
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

    def ryot_client() -> RyotClient:
        return RyotClient(
            base_url=str(settings.ryot_url),
            admin_access_token=settings.ryot_admin_access_token,
            timeout_seconds=settings.upstream_timeout_seconds,
        )

    @router.get("/jellyfin/library")
    async def jellyfin_library(
        start_index: int = Query(default=0, ge=0),
        limit: int | None = Query(default=None, ge=1, le=500),
    ) -> MediaSearchResponse:
        return await _map_upstream_errors(
            "jellyfin",
            lambda: jellyfin_client().library(start_index=start_index, limit=limit),
        )

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

    @router.get("/seerr/search")
    async def seerr_search(q: str) -> MediaSearchResponse:
        return await _map_upstream_errors("seerr", lambda: seerr_client().search(q))

    @router.post("/seerr/requests")
    async def seerr_request(
        request: SeerrRequestCreate,
    ) -> SeerrRequestResponse:
        if request.dry_run:
            return await _map_upstream_errors(
                "seerr",
                lambda: seerr_client().validate_request(
                    media_type=request.media_type,
                    tmdb_id=request.tmdb_id,
                ),
            )

        return await _map_upstream_errors(
            "seerr",
            lambda: seerr_client().create_request(
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

    @router.get("/ryot/probe")
    async def ryot_probe() -> RyotProbeResponse:
        return await _map_upstream_errors("ryot", ryot_client().probe)

    return router
