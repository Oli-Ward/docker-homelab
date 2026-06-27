from collections.abc import Awaitable, Callable

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from openclaw_gateway.auth import require_gateway_token
from openclaw_gateway.clients.jellyfin import JellyfinClient
from openclaw_gateway.clients.jellyseerr import JellyseerrClient
from openclaw_gateway.schemas.media import MediaSearchResponse
from openclaw_gateway.settings import GatewaySettings


async def _map_upstream_errors(
    upstream_name: str,
    request: Callable[[], Awaitable[MediaSearchResponse]],
) -> MediaSearchResponse:
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

    @router.get("/jellyfin/library")
    async def jellyfin_library() -> MediaSearchResponse:
        return await _map_upstream_errors("jellyfin", jellyfin_client().library)

    @router.get("/jellyfin/search")
    async def jellyfin_search(q: str) -> MediaSearchResponse:
        return await _map_upstream_errors("jellyfin", lambda: jellyfin_client().search(q))

    @router.get("/jellyseerr/search")
    async def jellyseerr_search(q: str) -> MediaSearchResponse:
        return await _map_upstream_errors("jellyseerr", lambda: jellyseerr_client().search(q))

    return router
