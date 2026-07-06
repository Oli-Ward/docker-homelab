import json

import httpx
import pytest
import respx

from openclaw_gateway.clients.ryot import RyotClient, RyotGraphQLError


@pytest.mark.asyncio
@respx.mock
async def test_ryot_probe_posts_fixed_graphql_query():
    route = respx.post("http://ryot:8000/backend/graphql").mock(
        return_value=httpx.Response(200, json={"data": {"__typename": "QueryRoot"}})
    )
    client = RyotClient(
        base_url="http://ryot:8000",
        admin_access_token="ryot-secret",
        timeout_seconds=5.0,
    )

    result = await client.probe()

    assert route.called
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer ryot-secret"
    assert request.headers["Content-Type"] == "application/json"
    assert json.loads(request.content)["query"] == "query OpenClawRyotProbe { __typename }"
    assert result.status == "ok"
    assert result.service == "ryot"
    assert result.typename == "QueryRoot"


@pytest.mark.asyncio
@respx.mock
async def test_ryot_probe_raises_on_graphql_errors():
    respx.post("http://ryot:8000/backend/graphql").mock(
        return_value=httpx.Response(
            200,
            json={"errors": [{"message": "not allowed"}]},
        )
    )
    client = RyotClient(
        base_url="http://ryot:8000",
        admin_access_token="ryot-secret",
        timeout_seconds=5.0,
    )

    with pytest.raises(RyotGraphQLError):
        await client.probe()


@pytest.mark.asyncio
@respx.mock
async def test_ryot_probe_raises_when_data_is_missing():
    respx.post("http://ryot:8000/backend/graphql").mock(
        return_value=httpx.Response(200, json={"data": None})
    )
    client = RyotClient(
        base_url="http://ryot:8000",
        admin_access_token="ryot-secret",
        timeout_seconds=5.0,
    )

    with pytest.raises(RyotGraphQLError):
        await client.probe()
