import httpx

from openclaw_gateway.schemas.media import (
    SeerrRequestResponse,
    MediaItem,
    MediaSearchResponse,
)


SEERR_AVAILABLE_STATUS = 5
REQUEST_STATUS_LABELS = {
    1: "pending",
    2: "approved",
    3: "declined",
}


class SeerrClient:
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

    async def validate_request(
        self,
        media_type: str,
        tmdb_id: int,
    ) -> SeerrRequestResponse:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}{self._detail_path(media_type, tmdb_id)}",
                headers={"X-Api-Key": self._api_key},
            )
            response.raise_for_status()

        return SeerrRequestResponse(
            status="valid",
            media_type=media_type,
            tmdb_id=tmdb_id,
            message="Request target is valid; no request was created.",
            request_id=None,
            duplicate=False,
            dry_run=True,
        )

    async def create_request(
        self,
        media_type: str,
        tmdb_id: int,
    ) -> SeerrRequestResponse:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/v1/request",
                headers={"X-Api-Key": self._api_key},
                json={"mediaType": media_type, "mediaId": tmdb_id},
            )

        if self._is_duplicate_request_response(response):
            return SeerrRequestResponse(
                status="duplicate",
                media_type=media_type,
                tmdb_id=tmdb_id,
                message="Media has already been requested.",
                request_id=None,
                duplicate=True,
                dry_run=False,
            )

        response.raise_for_status()
        payload = response.json()
        return SeerrRequestResponse(
            status="created",
            media_type=media_type,
            tmdb_id=tmdb_id,
            message="Seerr request created.",
            request_id=payload.get("id"),
            duplicate=False,
            dry_run=False,
        )

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
            available=media_info.get("status") == SEERR_AVAILABLE_STATUS,
            request_status=request_status,
        )

    def _is_duplicate_request_response(self, response: httpx.Response) -> bool:
        if response.status_code not in {409, 412}:
            return False

        try:
            message = str(response.json().get("message", ""))
        except ValueError:
            message = response.text

        normalized = message.lower()
        return "already" in normalized and "request" in normalized

    def _detail_path(self, media_type: str, tmdb_id: int) -> str:
        if media_type == "tv":
            return f"/api/v1/tv/{tmdb_id}"

        return f"/api/v1/movie/{tmdb_id}"
