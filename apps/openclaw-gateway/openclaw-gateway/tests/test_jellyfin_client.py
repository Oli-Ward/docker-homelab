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
    request = route.calls.last.request
    assert request.headers["X-Emby-Token"] == "jellyfin-secret"
    assert request.url.params["Recursive"] == "true"
    assert request.url.params["IncludeItemTypes"] == "Movie,Series"
    assert request.url.params["SearchTerm"] == "alien"
    assert result.items[0].id == "abc"
    assert result.items[0].type == "movie"
    assert result.items[0].title == "Alien"
    assert result.items[0].year == 1979
    assert result.items[0].overview == "Space horror"
    assert result.items[0].available is True


@pytest.mark.asyncio
@respx.mock
async def test_jellyfin_library_normalizes_items():
    route = respx.get("http://jellyfin:8096/Items").mock(
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

    assert route.called
    request = route.calls.last.request
    assert request.headers["X-Emby-Token"] == "jellyfin-secret"
    assert request.url.params["Recursive"] == "true"
    assert request.url.params["IncludeItemTypes"] == "Movie,Series"
    assert "SearchTerm" not in request.url.params
    assert result.items[0].id == "series-1"
    assert result.items[0].type == "series"
    assert result.items[0].title == "Severance"


@pytest.mark.asyncio
@respx.mock
async def test_jellyfin_library_normalizes_inventory_metadata():
    route = respx.get("http://jellyfin:8096/Items").mock(
        return_value=httpx.Response(
            200,
            json={
                "Items": [
                    {
                        "Id": "movie-1",
                        "Name": "Alien",
                        "Type": "Movie",
                        "ProductionYear": 1979,
                        "Overview": "Space horror",
                        "LibraryName": "Movies",
                        "RunTimeTicks": 70200000000,
                        "Genres": ["Horror", "Sci-Fi"],
                        "Path": "/media/movies/Alien (1979)/Alien.mkv",
                    }
                ],
                "TotalRecordCount": 147,
            },
        )
    )
    client = JellyfinClient(
        base_url="http://jellyfin:8096",
        api_key="jellyfin-secret",
        timeout_seconds=5.0,
    )

    result = await client.library(start_index=25, limit=50)

    assert route.called
    request = route.calls.last.request
    assert request.url.params["Recursive"] == "true"
    assert request.url.params["IncludeItemTypes"] == "Movie,Series"
    assert request.url.params["StartIndex"] == "25"
    assert request.url.params["Limit"] == "50"
    assert request.url.params["Fields"] == "Overview,Genres,RunTimeTicks"
    assert result.items[0].library == "Movies"
    assert result.items[0].runtime_minutes == 117
    assert result.items[0].genres == ["Horror", "Sci-Fi"]
    assert not hasattr(result.items[0], "path")
    assert result.pagination.mode == "window"
    assert result.pagination.start_index == 25
    assert result.pagination.limit == 50
    assert result.pagination.total == 147
