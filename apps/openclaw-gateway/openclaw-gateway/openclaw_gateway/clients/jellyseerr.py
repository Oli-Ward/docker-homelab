import httpx

from openclaw_gateway.schemas.media import MediaItem, MediaSearchResponse


JELLYSEERR_AVAILABLE_STATUS = 5
REQUEST_STATUS_LABELS = {
    1: "pending",
    2: "approved",
    3: "declined",
}


class JellyseerrClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = httpx.Timeout(timeout_seconds)

    async def search(self, query: str) -> MediaSearchResponse:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}/api/v1/search",
                headers={"X-Api-Key": self._api_key},
                params={"query": query},
            )
            response.raise_for_status()

        items = [self._normalize_item(item) for item in response.json().get("results", [])]
        return MediaSearchResponse(items=items)

    def _normalize_item(self, item: dict) -> MediaItem:
        media_info = item.get("mediaInfo") or {}
        requests = media_info.get("requests") or []
        request_status = None
        if requests:
            request_status = REQUEST_STATUS_LABELS.get(requests[0].get("status"), "unknown")

        title = item.get("title") or item.get("name") or item.get("originalTitle") or ""
        release_date = item.get("releaseDate") or item.get("firstAirDate") or ""
        year = (
            int(release_date[:4])
            if len(release_date) >= 4 and release_date[:4].isdigit()
            else None
        )

        return MediaItem(
            id=str(item.get("id", "")),
            type=str(item.get("mediaType", "unknown")).lower(),
            title=str(title),
            year=year,
            overview=item.get("overview"),
            available=media_info.get("status") == JELLYSEERR_AVAILABLE_STATUS,
            request_status=request_status,
        )
