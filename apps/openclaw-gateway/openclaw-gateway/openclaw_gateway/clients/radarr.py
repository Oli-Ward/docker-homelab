import httpx

from openclaw_gateway.schemas.media import (
    MovieStatistics,
    MovieSummary,
    MovieSummaryResponse,
)


class RadarrClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = httpx.Timeout(timeout_seconds)

    async def movies(self) -> MovieSummaryResponse:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}/api/v3/movie",
                headers={"X-Api-Key": self._api_key},
            )
            response.raise_for_status()

        items = [self._normalize_movie(item) for item in response.json()]
        return MovieSummaryResponse(items=items)

    def _normalize_movie(self, item: dict) -> MovieSummary:
        statistics = item.get("statistics") or {}
        return MovieSummary(
            id=str(item.get("id", "")),
            tmdb_id=item.get("tmdbId"),
            title=str(item.get("title", "")),
            year=item.get("year"),
            status=item.get("status"),
            monitored=bool(item.get("monitored", False)),
            has_file=bool(item.get("hasFile", False)),
            available=bool(item.get("isAvailable", False)),
            path=item.get("path"),
            quality_profile_id=item.get("qualityProfileId"),
            statistics=MovieStatistics(
                movie_file_count=statistics.get("movieFileCount"),
                size_on_disk=statistics.get("sizeOnDisk"),
            ),
            tags=list(item.get("tags") or []),
        )
