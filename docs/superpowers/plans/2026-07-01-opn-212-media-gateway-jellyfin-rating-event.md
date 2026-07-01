# OPN-212 Media Gateway Jellyfin Rating Event Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the media-host gateway side of OPN-212 so a completed Jellyfin movie watch event can be accepted as a narrow, token-protected payload and forwarded to the approved OpenClaw/n8n receiving path.

**Architecture:** Keep Jellyfin API keys and media-host routing inside the existing `openclaw-gateway` service. Add one fixed authenticated endpoint under `/v1/media/jellyfin/watch-completed` that accepts only completed movie payload fields, rejects non-movie or non-completed events, derives a stable dedupe key, and forwards the sanitized payload to one configured n8n webhook path. Document the Jellyfin UI/plugin setup and rollback steps without changing live Jellyfin state.

**Tech Stack:** Docker Compose, FastAPI, Pydantic, httpx, pytest, respx.

---

### Task 1: Add Gateway Contract Tests

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_media_routes.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_n8n_client.py`

- [ ] **Step 1: Add failing route tests**

Add these imports to `apps/openclaw-gateway/openclaw-gateway/tests/test_media_routes.py`:

```python
from openclaw_gateway.schemas.automation import RatingPromptForwardResponse
```

Add these tests near the Jellyfin route tests:

```python
@pytest.mark.asyncio
async def test_jellyfin_watch_completed_route_forwards_movie_prompt(monkeypatch):
    async def forward_rating_prompt(self, event):
        assert event.item_id == "jellyfin-movie-1"
        assert event.title == "Alien"
        assert event.year == 1979
        assert event.watched_at == "2026-07-01T07:10:00Z"
        assert event.user_id == "oli-profile"
        assert event.dedupe_key == "jellyfin-movie-1:2026-07-01T07:10:00Z"
        return RatingPromptForwardResponse(
            ok=True,
            workflow="jellyfin-rating-prompt",
            received=True,
            dedupe_key=event.dedupe_key,
        )

    monkeypatch.setattr(
        "openclaw_gateway.routers.media.N8nClient.forward_rating_prompt",
        forward_rating_prompt,
    )
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/media/jellyfin/watch-completed",
            headers={"Authorization": "Bearer gateway-secret"},
            json={
                "event": "playback.stop",
                "item_id": "jellyfin-movie-1",
                "item_type": "movie",
                "title": "Alien",
                "year": 1979,
                "watched_at": "2026-07-01T07:10:00Z",
                "user_id": "oli-profile",
                "completed": True,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "forwarded",
        "dedupe_key": "jellyfin-movie-1:2026-07-01T07:10:00Z",
        "forwarded": True,
        "message": "Completed movie event forwarded for rating prompt.",
    }


@pytest.mark.asyncio
async def test_jellyfin_watch_completed_route_rejects_non_movies(monkeypatch):
    async def forward_rating_prompt(self, event):
        raise AssertionError("non-movie events must not be forwarded")

    monkeypatch.setattr(
        "openclaw_gateway.routers.media.N8nClient.forward_rating_prompt",
        forward_rating_prompt,
    )
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/media/jellyfin/watch-completed",
            headers={"Authorization": "Bearer gateway-secret"},
            json={
                "event": "playback.stop",
                "item_id": "episode-1",
                "item_type": "episode",
                "title": "Episode One",
                "watched_at": "2026-07-01T07:10:00Z",
                "completed": True,
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_jellyfin_watch_completed_route_rejects_partial_playback(monkeypatch):
    async def forward_rating_prompt(self, event):
        raise AssertionError("partial playback must not be forwarded")

    monkeypatch.setattr(
        "openclaw_gateway.routers.media.N8nClient.forward_rating_prompt",
        forward_rating_prompt,
    )
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/media/jellyfin/watch-completed",
            headers={"Authorization": "Bearer gateway-secret"},
            json={
                "event": "playback.progress",
                "item_id": "jellyfin-movie-1",
                "item_type": "movie",
                "title": "Alien",
                "watched_at": "2026-07-01T07:10:00Z",
                "completed": False,
            },
        )

    assert response.status_code == 422
```

- [ ] **Step 2: Add failing n8n client test**

Append this test to `apps/openclaw-gateway/openclaw-gateway/tests/test_n8n_client.py`:

```python
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
```

Also add the needed imports:

```python
from openclaw_gateway.schemas.media import JellyfinWatchCompletedEvent
```

- [ ] **Step 3: Run tests to verify RED**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest tests/test_media_routes.py::test_jellyfin_watch_completed_route_forwards_movie_prompt tests/test_media_routes.py::test_jellyfin_watch_completed_route_rejects_non_movies tests/test_media_routes.py::test_jellyfin_watch_completed_route_rejects_partial_playback tests/test_n8n_client.py::test_n8n_forward_rating_prompt_posts_minimal_payload -q
```

Expected: FAIL because `RatingPromptForwardResponse`, `JellyfinWatchCompletedEvent`, and `/v1/media/jellyfin/watch-completed` do not exist yet.

### Task 2: Implement Event Models, Forwarding Client, and Route

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/media.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/automation.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/n8n.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/media.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/settings.py`

- [ ] **Step 1: Add schemas**

Add to `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/media.py`:

```python
class JellyfinWatchCompletedEvent(BaseModel):
    event: str
    item_id: Annotated[str, Field(min_length=1)]
    item_type: Literal["movie"]
    title: Annotated[str, Field(min_length=1)]
    year: int | None = None
    watched_at: Annotated[str, Field(min_length=1)]
    user_id: str | None = None
    completed: Literal[True]

    @property
    def dedupe_key(self) -> str:
        return f"{self.item_id}:{self.watched_at}"


class JellyfinWatchCompletedResponse(BaseModel):
    status: Literal["forwarded"]
    dedupe_key: str
    forwarded: bool
    message: str
```

Add to `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/automation.py`:

```python
class RatingPromptForwardResponse(BaseModel):
    ok: bool
    workflow: str
    received: bool
    dedupe_key: str
```

- [ ] **Step 2: Add setting**

Add to `GatewaySettings` in `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/settings.py`:

```python
    n8n_jellyfin_rating_prompt_path: Annotated[
        str,
        Field(min_length=1, pattern=r"^/webhook/[A-Za-z0-9._~!$&'()*+,;=:@/-]+$"),
    ]
```

- [ ] **Step 3: Extend the n8n client**

Change `N8nClient.__init__` to accept `rating_prompt_path`, store it, and add:

```python
    async def forward_rating_prompt(
        self, event: JellyfinWatchCompletedEvent
    ) -> RatingPromptForwardResponse:
        payload = {
            "source": "jellyfin",
            "event": "watch_completed",
            "item_id": event.item_id,
            "title": event.title,
            "year": event.year,
            "watched_at": event.watched_at,
            "user_id": event.user_id,
            "dedupe_key": event.dedupe_key,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(f"{self._base_url}{self._rating_prompt_path}", json=payload)
            response.raise_for_status()

        return RatingPromptForwardResponse.model_validate(response.json())
```

- [ ] **Step 4: Add the media route**

In `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/media.py`, import `N8nClient`, `JellyfinWatchCompletedEvent`, and `JellyfinWatchCompletedResponse`. Add an `n8n_client()` factory using `settings.n8n_webhook_base_url`, `settings.n8n_jellyfin_rating_prompt_path`, and `settings.upstream_timeout_seconds`.

Add this route:

```python
    @router.post("/jellyfin/watch-completed")
    async def jellyfin_watch_completed(
        event: JellyfinWatchCompletedEvent,
    ) -> JellyfinWatchCompletedResponse:
        await _map_upstream_errors(
            "n8n",
            lambda: n8n_client().forward_rating_prompt(event),
        )
        return JellyfinWatchCompletedResponse(
            status="forwarded",
            dedupe_key=event.dedupe_key,
            forwarded=True,
            message="Completed movie event forwarded for rating prompt.",
        )
```

- [ ] **Step 5: Run tests to verify GREEN**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest tests/test_media_routes.py::test_jellyfin_watch_completed_route_forwards_movie_prompt tests/test_media_routes.py::test_jellyfin_watch_completed_route_rejects_non_movies tests/test_media_routes.py::test_jellyfin_watch_completed_route_rejects_partial_playback tests/test_n8n_client.py::test_n8n_forward_rating_prompt_posts_minimal_payload -q
```

Expected: PASS.

### Task 3: Wire Compose Env and Documentation

**Files:**
- Modify: `apps/openclaw-gateway/compose.yml`
- Modify: `apps/openclaw-gateway/example.env`
- Modify: `apps/openclaw-gateway/README.md`

- [ ] **Step 1: Add the compose environment variable**

Add to `apps/openclaw-gateway/compose.yml` under the existing n8n variables:

```yaml
      - N8N_JELLYFIN_RATING_PROMPT_PATH=${N8N_JELLYFIN_RATING_PROMPT_PATH:-/webhook/jellyfin-rating-prompt}
```

- [ ] **Step 2: Add the example env placeholder**

Add to `apps/openclaw-gateway/example.env`:

```dotenv
N8N_JELLYFIN_RATING_PROMPT_PATH=/webhook/jellyfin-rating-prompt
```

- [ ] **Step 3: Document the endpoint and rollout**

Update `apps/openclaw-gateway/README.md` endpoint list with:

```text
POST /v1/media/jellyfin/watch-completed
```

Document that the endpoint accepts:

```json
{
  "event": "playback.stop",
  "item_id": "jellyfin-movie-1",
  "item_type": "movie",
  "title": "Alien",
  "year": 1979,
  "watched_at": "2026-07-01T07:10:00Z",
  "user_id": "oli-profile",
  "completed": true
}
```

Document that the gateway forwards only:

```json
{
  "source": "jellyfin",
  "event": "watch_completed",
  "item_id": "jellyfin-movie-1",
  "title": "Alien",
  "year": 1979,
  "watched_at": "2026-07-01T07:10:00Z",
  "user_id": "oli-profile",
  "dedupe_key": "jellyfin-movie-1:2026-07-01T07:10:00Z"
}
```

Document the rollout checklist:

```text
1. Deploy the updated openclaw-gateway stack through Komodo.
2. Create or enable the n8n workflow at /webhook/jellyfin-rating-prompt.
3. Configure Jellyfin's webhook/notification plugin from the Jellyfin admin UI to POST only completed movie events to /v1/media/jellyfin/watch-completed with the gateway bearer token.
4. Smoke test with the documented curl command before relying on real playback events.
5. Disable rollback by disabling the Jellyfin webhook/plugin entry or rotating/removing the gateway token.
```

- [ ] **Step 4: Validate config and tests**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest -q
```

Run from repo root:

```bash
docker compose --env-file apps/openclaw-gateway/example.env -f apps/openclaw-gateway/compose.yml config >/tmp/opn-212-openclaw-gateway-compose.yml
git diff --check
```

Expected: tests pass, compose config renders, and `git diff --check` exits 0.

### Task 4: Linear Update and Handoff

**Files:**
- No file changes.

- [ ] **Step 1: Re-read acceptance criteria**

Confirm:

```text
- Confirm available Jellyfin webhook/notification mechanism: documented as Jellyfin admin UI/plugin rollout, not repo-managed.
- Define payload and auth: README endpoint docs and bearer token route.
- OpenClaw receives/can retrieve event: gateway endpoint accepts event and forwards to n8n/OpenClaw path.
- OpenClaw asks for rating: delegated to n8n/OpenClaw workflow; this repo forwards the event.
- Duplicate prompts: dedupe key is forwarded; final suppression remains in OpenClaw workflow/storage.
- Rating storage: remains the existing OpenClaw follow-up from prior OPN-212 slice.
- Rollback/disable: README documents disabling Jellyfin webhook/plugin or token rotation.
- Smoke test: README curl and tests cover simulated event path.
```

- [ ] **Step 2: Add a Linear comment**

Comment with:

```markdown
Picked up the media-host repo slice for OPN-212.

Outcome:
- Added a token-protected gateway endpoint for completed Jellyfin movie events.
- Added a fixed n8n/OpenClaw forwarding path and documented the minimal payload.
- Documented Jellyfin plugin/UI rollout and disable/rollback steps.

Verification:
- `pytest -q` in `apps/openclaw-gateway/openclaw-gateway`
- `docker compose --env-file apps/openclaw-gateway/example.env -f apps/openclaw-gateway/compose.yml config`
- `git diff --check`

Remaining:
- Deploy via Komodo.
- Configure the Jellyfin webhook/notification plugin in the Jellyfin UI.
- Create/enable the n8n `/webhook/jellyfin-rating-prompt` workflow and OpenClaw rating prompt handling.
- Keep OPN-212 blocked or partially active until those external rollout steps are done.
```
