import httpx

from openclaw_gateway.schemas.media import (
    SeriesStatistics,
    SeriesSummary,
    SeriesSummaryResponse,
)


class SonarrClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = httpx.Timeout(timeout_seconds)

    async def series(self) -> SeriesSummaryResponse:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}/api/v3/series",
                headers={"X-Api-Key": self._api_key},
            )
            response.raise_for_status()

        items = [self._normalize_series(item) for item in response.json()]
        return SeriesSummaryResponse(items=items)

    def _normalize_series(self, item: dict) -> SeriesSummary:
        statistics = item.get("statistics") or {}
        return SeriesSummary(
            id=str(item.get("id", "")),
            tvdb_id=item.get("tvdbId"),
            title=str(item.get("title", "")),
            year=item.get("year"),
            status=item.get("status"),
            monitored=bool(item.get("monitored", False)),
            path=item.get("path"),
            quality_profile_id=item.get("qualityProfileId"),
            statistics=SeriesStatistics(
                season_count=statistics.get("seasonCount"),
                episode_file_count=statistics.get("episodeFileCount"),
                episode_count=statistics.get("episodeCount"),
                total_episode_count=statistics.get("totalEpisodeCount"),
                size_on_disk=statistics.get("sizeOnDisk"),
            ),
            tags=list(item.get("tags") or []),
        )
