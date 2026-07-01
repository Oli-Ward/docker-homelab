import httpx
import pytest
import respx

from openclaw_gateway.clients.n8n import N8nClient
from openclaw_gateway.schemas.media import JellyfinWatchCompletedEvent


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
        rating_prompt_path="/webhook/jellyfin-rating-prompt",
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
