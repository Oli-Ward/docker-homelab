import httpx
import pytest
import respx

from openclaw_gateway.clients.radarr import RadarrClient


@pytest.mark.asyncio
@respx.mock
async def test_radarr_movies_returns_normalized_summaries():
    route = respx.get("http://radarr:7878/api/v3/movie").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": 34,
                    "tmdbId": 348,
                    "title": "Alien",
                    "year": 1979,
                    "status": "released",
                    "monitored": True,
                    "hasFile": True,
                    "isAvailable": True,
                    "path": "/movies/Alien (1979)",
                    "qualityProfileId": 2,
                    "statistics": {
                        "movieFileCount": 1,
                        "sizeOnDisk": 987654321,
                    },
                    "tags": [7],
                }
            ],
        )
    )

    client = RadarrClient(
        base_url="http://radarr:7878",
        api_key="radarr-secret",
        timeout_seconds=5.0,
    )

    response = await client.movies()

    assert route.calls.last.request.headers["X-Api-Key"] == "radarr-secret"
    assert response.model_dump() == {
        "items": [
            {
                "id": "34",
                "tmdb_id": 348,
                "title": "Alien",
                "year": 1979,
                "status": "released",
                "monitored": True,
                "has_file": True,
                "available": True,
                "path": "/movies/Alien (1979)",
                "quality_profile_id": 2,
                "statistics": {
                    "movie_file_count": 1,
                    "size_on_disk": 987654321,
                },
                "tags": [7],
            }
        ]
    }
