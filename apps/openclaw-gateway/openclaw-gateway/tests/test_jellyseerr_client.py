import httpx
import pytest
import respx

from openclaw_gateway.clients.jellyseerr import JellyseerrClient


@pytest.mark.asyncio
@respx.mock
async def test_jellyseerr_search_normalizes_results():
    route = respx.get("http://jellyseerr:5055/api/v1/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": 348,
                        "mediaType": "movie",
                        "title": "Alien",
                        "releaseDate": "1979-05-25",
                        "overview": "Space horror",
                        "mediaInfo": {
                            "status": 5,
                            "requests": [{"status": 2}],
                        },
                    }
                ]
            },
        )
    )
    client = JellyseerrClient(
        base_url="http://jellyseerr:5055",
        api_key="jellyseerr-secret",
        timeout_seconds=5.0,
    )

    result = await client.search("alien")

    assert route.called
    request = route.calls.last.request
    assert request.headers["X-Api-Key"] == "jellyseerr-secret"
    assert request.url.params["query"] == "alien"
    assert result.items[0].id == "348"
    assert result.items[0].type == "movie"
    assert result.items[0].title == "Alien"
    assert result.items[0].year == 1979
    assert result.items[0].overview == "Space horror"
    assert result.items[0].available is True
    assert result.items[0].request_status == "approved"
