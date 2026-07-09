import httpx
import pytest
import respx

from openclaw_gateway.clients.seerr import SeerrClient


@pytest.mark.asyncio
@respx.mock
async def test_seerr_search_normalizes_results():
    route = respx.get("http://seerr:5055/api/v1/search").mock(
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
    client = SeerrClient(
        base_url="http://seerr:5055",
        api_key="seerr-secret",
        timeout_seconds=5.0,
    )

    result = await client.search("alien")

    assert route.called
    request = route.calls.last.request
    assert request.headers["X-Api-Key"] == "seerr-secret"
    assert request.url.params["query"] == "alien"
    assert result.items[0].id == "348"
    assert result.items[0].type == "movie"
    assert result.items[0].title == "Alien"
    assert result.items[0].year == 1979
    assert result.items[0].overview == "Space horror"
    assert result.items[0].available is True
    assert result.items[0].request_status == "approved"


@pytest.mark.asyncio
@respx.mock
async def test_seerr_create_request_posts_narrow_payload():
    route = respx.post("http://seerr:5055/api/v1/request").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": 77,
                "type": "movie",
                "media": {"tmdbId": 348},
            },
        )
    )
    client = SeerrClient(
        base_url="http://seerr:5055",
        api_key="seerr-secret",
        timeout_seconds=5.0,
    )

    result = await client.create_request(media_type="movie", tmdb_id=348)

    assert route.called
    request = route.calls.last.request
    assert request.headers["X-Api-Key"] == "seerr-secret"
    assert request.read() == b'{"mediaType":"movie","mediaId":348}'
    assert result.status == "created"
    assert result.request_id == 77
    assert result.duplicate is False
    assert result.dry_run is False


@pytest.mark.asyncio
@respx.mock
async def test_seerr_create_request_maps_duplicate_response():
    respx.post("http://seerr:5055/api/v1/request").mock(
        return_value=httpx.Response(
            409,
            json={"message": "Media has already been requested"},
        )
    )
    client = SeerrClient(
        base_url="http://seerr:5055",
        api_key="seerr-secret",
        timeout_seconds=5.0,
    )

    result = await client.create_request(media_type="tv", tmdb_id=12345)

    assert result.status == "duplicate"
    assert result.media_type == "tv"
    assert result.tmdb_id == 12345
    assert result.request_id is None
    assert result.duplicate is True
    assert result.dry_run is False


@pytest.mark.asyncio
@respx.mock
async def test_seerr_validate_movie_request_fetches_tmdb_detail_without_posting():
    detail_route = respx.get("http://seerr:5055/api/v1/movie/348").mock(
        return_value=httpx.Response(
            200,
            json={"id": 348, "title": "Alien"},
        )
    )
    request_route = respx.post("http://seerr:5055/api/v1/request").mock(
        return_value=httpx.Response(201, json={"id": 77})
    )
    client = SeerrClient(
        base_url="http://seerr:5055",
        api_key="seerr-secret",
        timeout_seconds=5.0,
    )

    result = await client.validate_request(media_type="movie", tmdb_id=348)

    assert detail_route.called
    assert not request_route.called
    assert result.status == "valid"
    assert result.duplicate is False
    assert result.dry_run is True


@pytest.mark.asyncio
@respx.mock
async def test_seerr_validate_tv_request_fetches_tmdb_detail_without_posting():
    detail_route = respx.get("http://seerr:5055/api/v1/tv/1399").mock(
        return_value=httpx.Response(
            200,
            json={"id": 1399, "name": "Game of Thrones"},
        )
    )
    request_route = respx.post("http://seerr:5055/api/v1/request").mock(
        return_value=httpx.Response(201, json={"id": 77})
    )
    client = SeerrClient(
        base_url="http://seerr:5055",
        api_key="seerr-secret",
        timeout_seconds=5.0,
    )

    result = await client.validate_request(media_type="tv", tmdb_id=1399)

    assert detail_route.called
    assert not request_route.called
    assert result.status == "valid"
    assert result.duplicate is False
    assert result.dry_run is True


@pytest.mark.asyncio
@respx.mock
async def test_seerr_validate_request_requires_existing_tmdb_detail():
    respx.get("http://seerr:5055/api/v1/movie/348").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )
    client = SeerrClient(
        base_url="http://seerr:5055",
        api_key="seerr-secret",
        timeout_seconds=5.0,
    )

    with pytest.raises(httpx.HTTPStatusError) as exc:
        await client.validate_request(media_type="movie", tmdb_id=348)

    assert exc.value.response.status_code == 404
