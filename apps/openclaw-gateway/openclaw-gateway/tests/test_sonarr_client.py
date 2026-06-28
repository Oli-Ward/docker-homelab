import httpx
import pytest
import respx

from openclaw_gateway.clients.sonarr import SonarrClient


@pytest.mark.asyncio
@respx.mock
async def test_sonarr_series_returns_normalized_summaries():
    route = respx.get("http://sonarr:8989/api/v3/series").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": 12,
                    "tvdbId": 12345,
                    "title": "Severance",
                    "year": 2022,
                    "status": "continuing",
                    "monitored": True,
                    "path": "/tv/Severance",
                    "qualityProfileId": 3,
                    "statistics": {
                        "seasonCount": 2,
                        "episodeFileCount": 10,
                        "episodeCount": 19,
                        "totalEpisodeCount": 19,
                        "sizeOnDisk": 123456789,
                    },
                    "tags": [4, 9],
                }
            ],
        )
    )

    client = SonarrClient(
        base_url="http://sonarr:8989",
        api_key="sonarr-secret",
        timeout_seconds=5.0,
    )

    response = await client.series()

    assert route.calls.last.request.headers["X-Api-Key"] == "sonarr-secret"
    assert response.model_dump() == {
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
