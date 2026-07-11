import httpx
import pytest
import respx

from openclaw_gateway.clients.n8n import N8nClient
from openclaw_gateway.schemas.media import JellyfinWatchCompletedEvent


@pytest.mark.asyncio
@respx.mock
async def test_openclaw_smoke_posts_fixed_payload_and_parses_response():
    route = respx.post("http://n8n:5678/webhook/openclaw-smoke").mock(
        return_value=httpx.Response(
            200,
            json={"ok": True, "workflow": "openclaw-smoke", "received": True},
        )
    )
    client = N8nClient(
        base_url="http://n8n:5678",
        smoke_path="/webhook/openclaw-smoke",
        rating_prompt_path="/webhook/jellyfin-rating-prompt",
        plane_dispatch_path="/webhook/plane-openclaw-dispatch",
        timeout_seconds=5.0,
    )

    result = await client.openclaw_smoke(request_id="req-123")

    assert route.called
    request = route.calls.last.request
    assert request.headers["Content-Type"] == "application/json"
    assert request.content == b'{"source":"openclaw","test":true,"request_id":"req-123"}'
    assert result.ok is True
    assert result.workflow == "openclaw-smoke"
    assert result.received is True


@pytest.mark.asyncio
@respx.mock
async def test_n8n_forward_rating_prompt_posts_minimal_payload():
    route = respx.post("http://n8n:5678/webhook/jellyfin-rating-prompt").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "workflow": "jellyfin-rating-prompt",
                "received": True,
                "dedupe_key": "movie-1:2026-07-01T07:10:00Z",
            },
        )
    )
    client = N8nClient(
        base_url="http://n8n:5678",
        smoke_path="/webhook/openclaw-smoke",
        rating_prompt_path="/webhook/jellyfin-rating-prompt",
        plane_dispatch_path="/webhook/plane-openclaw-dispatch",
        timeout_seconds=5.0,
    )
    event = JellyfinWatchCompletedEvent(
        event="playback.stop",
        item_id="movie-1",
        item_type="movie",
        title="Alien",
        year=1979,
        watched_at="2026-07-01T07:10:00Z",
        user_id="oli-profile",
        completed=True,
    )

    result = await client.forward_rating_prompt(event)

    assert route.called
    assert route.calls.last.request.content == (
        b'{"source":"jellyfin","event":"watch_completed","item_id":"movie-1",'
        b'"title":"Alien","year":1979,"watched_at":"2026-07-01T07:10:00Z",'
        b'"user_id":"oli-profile","dedupe_key":"movie-1:2026-07-01T07:10:00Z"}'
    )
    assert result.ok is True
    assert result.workflow == "jellyfin-rating-prompt"
    assert result.received is True
    assert result.dedupe_key == "movie-1:2026-07-01T07:10:00Z"


@pytest.mark.asyncio
@respx.mock
async def test_n8n_forward_plane_webhook_event_posts_normalized_payload():
    route = respx.post("http://n8n:5678/webhook/plane-openclaw-dispatch").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "workflow": "plane-openclaw-dispatch",
                "received": True,
                "correlation_id": "plane:delivery-1",
            },
        )
    )
    client = N8nClient(
        base_url="http://n8n:5678",
        smoke_path="/webhook/openclaw-smoke",
        rating_prompt_path="/webhook/jellyfin-rating-prompt",
        plane_dispatch_path="/webhook/plane-openclaw-dispatch",
        timeout_seconds=5.0,
    )

    result = await client.forward_plane_webhook_event(
        {
            "correlation_id": "plane:delivery-1",
            "delivery_id": "delivery-1",
            "event": "issue",
            "action": "update",
            "resource_id": "work-item-1",
            "webhook_id": "webhook-1",
            "actor_id": "human-user-1",
        }
    )

    assert route.called
    assert route.calls.last.request.content == (
        b'{"source":"plane","event":"issue","action":"update",'
        b'"correlation_id":"plane:delivery-1","delivery_id":"delivery-1",'
        b'"resource_id":"work-item-1","webhook_id":"webhook-1","actor_id":"human-user-1"}'
    )
    assert result == {
        "ok": True,
        "workflow": "plane-openclaw-dispatch",
        "received": True,
        "correlation_id": "plane:delivery-1",
    }
