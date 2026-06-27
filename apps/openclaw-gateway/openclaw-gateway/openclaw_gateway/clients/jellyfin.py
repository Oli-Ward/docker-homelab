import httpx

from openclaw_gateway.schemas.media import MediaItem, MediaSearchResponse


class JellyfinClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = httpx.Timeout(timeout_seconds)

    async def library(self) -> MediaSearchResponse:
        return await self._items(params={"Recursive": "true", "IncludeItemTypes": "Movie,Series"})

    async def search(self, query: str) -> MediaSearchResponse:
        return await self._items(
            params={
                "Recursive": "true",
                "SearchTerm": query,
                "IncludeItemTypes": "Movie,Series",
            }
        )

    async def _items(self, params: dict[str, str]) -> MediaSearchResponse:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}/Items",
                headers={"X-Emby-Token": self._api_key},
                params=params,
            )
            response.raise_for_status()

        items = [self._normalize_item(item) for item in response.json().get("Items", [])]
        return MediaSearchResponse(items=items)

    def _normalize_item(self, item: dict) -> MediaItem:
        return MediaItem(
            id=str(item.get("Id", "")),
            type=str(item.get("Type", "unknown")).lower(),
            title=str(item.get("Name", "")),
            year=item.get("ProductionYear"),
            overview=item.get("Overview"),
            available=True,
        )
