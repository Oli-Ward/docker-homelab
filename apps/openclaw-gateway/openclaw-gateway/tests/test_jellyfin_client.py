import httpx
import pytest
import respx

from openclaw_gateway.clients.jellyfin import JellyfinClient


@pytest.mark.asyncio
@respx.mock
async def test_jellyfin_search_normalizes_items():
    route = respx.get("http://jellyfin:8096/Items").mock(
        return_value=httpx.Response(
            200,
            json={
                "Items": [
                    {
                        "Id": "abc",
                        "Name": "Alien",
                        "Type": "Movie",
                        "ProductionYear": 1979,
                        "Overview": "Space horror",
                    }
                ]
            },
        )
    )
    client = JellyfinClient(
        base_url="http://jellyfin:8096",
        api_key="jellyfin-secret",
        timeout_seconds=5.0,
    )

    result = await client.search("alien")

    assert route.called
    assert result.items[0].id == "abc"
    assert result.items[0].type == "movie"
    assert result.items[0].title == "Alien"
    assert result.items[0].year == 1979
    assert result.items[0].overview == "Space horror"
    assert result.items[0].available is True


@pytest.mark.asyncio
@respx.mock
async def test_jellyfin_library_normalizes_items():
    respx.get("http://jellyfin:8096/Items").mock(
        return_value=httpx.Response(
            200,
            json={
                "Items": [
                    {
                        "Id": "series-1",
                        "Name": "Severance",
                        "Type": "Series",
                        "ProductionYear": 2022,
                    }
                ]
            },
        )
    )
    client = JellyfinClient(
        base_url="http://jellyfin:8096",
        api_key="jellyfin-secret",
        timeout_seconds=5.0,
    )

    result = await client.library()

    assert result.items[0].id == "series-1"
    assert result.items[0].type == "series"
    assert result.items[0].title == "Severance"
