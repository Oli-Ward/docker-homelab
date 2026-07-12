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
            "schema_version": "plane.webhook.v1",
            "event_id": "delivery-1",
            "event_type": "work_item.updated",
            "correlation_id": "plane:delivery-1",
            "idempotency_key": "delivery-1",
            "delivery_id": "delivery-1",
            "event": "issue",
            "action": "update",
            "resource_id": "work-item-1",
            "webhook_id": "webhook-1",
            "actor_id": "human-user-1",
            "team": "Openclaw",
            "project_id": "project-1",
            "source_identifier": "OPN-273",
            "sequence_id": 273,
            "name": "Ready for agent",
            "state_id": "state-ready",
            "state_name": "Ready for Agent",
            "priority": "high",
            "label_names": ["agent:ready", "repo:docker"],
            "origin": "plane",
            "retry_attempt": 0,
            "raw_payload_hash": "a" * 64,
            "description_html": "<p>must not forward</p>",
        }
    )

    assert route.called
    assert route.calls.last.request.content == (
        b'{"schema_version":"plane.webhook.v1","event_id":"delivery-1",'
        b'"event_type":"work_item.updated","idempotency_key":"delivery-1",'
        b'"correlation_id":"plane:delivery-1","causation_id":null,"origin":"plane",'
        b'"retry_attempt":0,"raw_payload_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
        b'"source":"plane","event":"issue","action":"update","delivery_id":"delivery-1",'
        b'"resource_id":"work-item-1","webhook_id":"webhook-1","actor_id":"human-user-1",'
        b'"team":"Openclaw",'
        b'"project_id":"project-1","source_identifier":"OPN-273","sequence_id":273,"name":"Ready for agent",'
        b'"state_id":"state-ready","state_name":"Ready for Agent","priority":"high",'
        b'"label_names":["agent:ready","repo:docker"]}'
    )
    assert result.ok is True
    assert result.failure_type is None
    assert result.error_code is None


@pytest.mark.asyncio
@respx.mock
async def test_n8n_forward_plane_webhook_event_classifies_permanent_failure() -> None:
    respx.post("http://n8n:5678/webhook/plane-openclaw-dispatch").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": False,
                "failure_type": "permanent",
                "error_code": "invalid_idempotency_key",
                "detail": "bad key",
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
            "event_id": "delivery-1",
            "correlation_id": "plane:delivery-1",
            "delivery_id": "delivery-1",
        }
    )

    assert result.ok is False
    assert result.failure_type == "permanent"
    assert result.error_code == "invalid_idempotency_key"
