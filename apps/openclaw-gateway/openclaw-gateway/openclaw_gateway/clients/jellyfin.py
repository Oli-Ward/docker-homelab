from typing import Any

import httpx

from openclaw_gateway.schemas.media import MediaItem, MediaPagination, MediaSearchResponse


class JellyfinClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = httpx.Timeout(timeout_seconds)

    async def library(self, start_index: int = 0, limit: int | None = None) -> MediaSearchResponse:
        params = {
            "Recursive": "true",
            "IncludeItemTypes": "Movie,Series",
            "Fields": "Overview,Genres,RunTimeTicks",
            "StartIndex": str(start_index),
        }
        if limit is not None:
            params["Limit"] = str(limit)

        return await self._items(params=params, start_index=start_index, limit=limit)

    async def search(self, query: str) -> MediaSearchResponse:
        return await self._items(
            params={
                "Recursive": "true",
                "SearchTerm": query,
                "IncludeItemTypes": "Movie,Series",
            }
        )

    async def _items(
        self,
        params: dict[str, str],
        start_index: int = 0,
        limit: int | None = None,
    ) -> MediaSearchResponse:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}/Items",
                headers={"X-Emby-Token": self._api_key},
                params=params,
            )
            response.raise_for_status()

        payload = response.json()
        items = [self._normalize_item(item) for item in payload.get("Items", [])]
        return MediaSearchResponse(
            items=items,
            pagination=MediaPagination(
                mode="window" if limit is not None or start_index > 0 else "full_response",
                start_index=start_index,
                limit=limit,
                total=payload.get("TotalRecordCount"),
            ),
        )

    def _normalize_item(self, item: dict[str, Any]) -> MediaItem:
        return MediaItem(
            id=str(item.get("Id", "")),
            type=str(item.get("Type", "unknown")).lower(),
            title=str(item.get("Name", "")),
            year=item.get("ProductionYear"),
            overview=item.get("Overview"),
            available=True,
            library=item.get("LibraryName") or item.get("CollectionName"),
            runtime_minutes=self._runtime_minutes(item.get("RunTimeTicks")),
            genres=[str(genre) for genre in item.get("Genres", []) if genre],
        )

    def _runtime_minutes(self, runtime_ticks: Any) -> int | None:
        if runtime_ticks is None:
            return None

        try:
            return round(int(runtime_ticks) / 600_000_000)
        except (TypeError, ValueError):
            return None
