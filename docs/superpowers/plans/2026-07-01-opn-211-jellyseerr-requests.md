# OPN-211 Jellyseerr Requests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let OpenClaw create narrowly shaped Jellyseerr media requests through the OpenClaw gateway without exposing raw Jellyseerr access.

**Architecture:** Extend the existing FastAPI media router with `POST /v1/media/jellyseerr/requests`. The route accepts a small schema, optionally performs a dry-run search validation, and delegates real request creation to `JellyseerrClient`, which calls only Jellyseerr's `POST /api/v1/request` endpoint and maps duplicate/already-requested responses to a clean gateway result.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, httpx, pytest, pytest-asyncio, respx, Docker Compose.

---

### Task 1: Add Request Schemas

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/media.py`
- Test: `apps/openclaw-gateway/openclaw-gateway/tests/test_media_routes.py`

- [ ] **Step 1: Write the failing route test for dry-run validation**

Add this test to `apps/openclaw-gateway/openclaw-gateway/tests/test_media_routes.py`:

```python
@pytest.mark.asyncio
async def test_jellyseerr_request_route_dry_run_validates_without_creating(monkeypatch):
    async def validate_request(self, media_type: str, tmdb_id: int):
        assert media_type == "movie"
        assert tmdb_id == 348
        return JellyseerrRequestResponse(
            status="valid",
            media_type="movie",
            tmdb_id=348,
            message="Request target is valid; no request was created.",
            request_id=None,
            duplicate=False,
            dry_run=True,
        )

    monkeypatch.setattr(
        "openclaw_gateway.routers.media.JellyseerrClient.validate_request",
        validate_request,
    )
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/media/jellyseerr/requests",
            headers={"Authorization": "Bearer gateway-secret"},
            json={
                "media_type": "movie",
                "tmdb_id": 348,
                "note": "requested by OpenClaw",
                "dry_run": True,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "valid",
        "media_type": "movie",
        "tmdb_id": 348,
        "message": "Request target is valid; no request was created.",
        "request_id": None,
        "duplicate": False,
        "dry_run": True,
    }
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest tests/test_media_routes.py::test_jellyseerr_request_route_dry_run_validates_without_creating -q
```

Expected: FAIL because `JellyseerrRequestResponse` and the route do not exist yet.

- [ ] **Step 3: Add schema imports and models**

In `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/media.py`, add:

```python
from typing import Literal
```

Then add:

```python
class JellyseerrRequestCreate(BaseModel):
    media_type: Literal["movie", "tv"]
    tmdb_id: int
    note: str | None = None
    dry_run: bool = True


class JellyseerrRequestResponse(BaseModel):
    status: Literal["created", "duplicate", "valid"]
    media_type: Literal["movie", "tv"]
    tmdb_id: int
    message: str
    request_id: int | None = None
    duplicate: bool
    dry_run: bool
```

- [ ] **Step 4: Run the test and keep the expected route failure**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest tests/test_media_routes.py::test_jellyseerr_request_route_dry_run_validates_without_creating -q
```

Expected: FAIL with HTTP 404 or missing route, proving the schema import is now available and the route is still missing.

### Task 2: Add Jellyseerr Client Request Behavior

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/jellyseerr.py`
- Test: `apps/openclaw-gateway/openclaw-gateway/tests/test_jellyseerr_client.py`

- [ ] **Step 1: Write the failing client tests**

Add these tests to `apps/openclaw-gateway/openclaw-gateway/tests/test_jellyseerr_client.py`:

```python
@pytest.mark.asyncio
@respx.mock
async def test_jellyseerr_create_request_posts_narrow_payload():
    route = respx.post("http://jellyseerr:5055/api/v1/request").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": 77,
                "type": "movie",
                "media": {"tmdbId": 348},
            },
        )
    )
    client = JellyseerrClient(
        base_url="http://jellyseerr:5055",
        api_key="jellyseerr-secret",
        timeout_seconds=5.0,
    )

    result = await client.create_request(media_type="movie", tmdb_id=348)

    assert route.called
    request = route.calls.last.request
    assert request.headers["X-Api-Key"] == "jellyseerr-secret"
    assert request.read() == b'{"mediaType":"movie","mediaId":348}'
    assert result.status == "created"
    assert result.request_id == 77
    assert result.duplicate is False
    assert result.dry_run is False


@pytest.mark.asyncio
@respx.mock
async def test_jellyseerr_create_request_maps_duplicate_response():
    respx.post("http://jellyseerr:5055/api/v1/request").mock(
        return_value=httpx.Response(
            409,
            json={"message": "Media has already been requested"},
        )
    )
    client = JellyseerrClient(
        base_url="http://jellyseerr:5055",
        api_key="jellyseerr-secret",
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
async def test_jellyseerr_validate_request_searches_without_posting():
    search_route = respx.get("http://jellyseerr:5055/api/v1/search").mock(
        return_value=httpx.Response(
            200,
            json={"results": [{"id": 348, "mediaType": "movie", "title": "Alien"}]},
        )
    )
    request_route = respx.post("http://jellyseerr:5055/api/v1/request").mock(
        return_value=httpx.Response(201, json={"id": 77})
    )
    client = JellyseerrClient(
        base_url="http://jellyseerr:5055",
        api_key="jellyseerr-secret",
        timeout_seconds=5.0,
    )

    result = await client.validate_request(media_type="movie", tmdb_id=348)

    assert search_route.called
    assert not request_route.called
    assert search_route.calls.last.request.url.params["query"] == "348"
    assert result.status == "valid"
    assert result.duplicate is False
    assert result.dry_run is True
```

- [ ] **Step 2: Run client tests to verify they fail**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest tests/test_jellyseerr_client.py -q
```

Expected: FAIL because `create_request` and `validate_request` do not exist.

- [ ] **Step 3: Implement client methods**

In `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/jellyseerr.py`, import `JellyseerrRequestResponse` and add `create_request`, `validate_request`, and a duplicate helper. The client must call only `/api/v1/request`, send `{"mediaType": media_type, "mediaId": tmdb_id}`, and return a normalized response instead of exposing raw Jellyseerr payloads.

- [ ] **Step 4: Run client tests to verify they pass**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest tests/test_jellyseerr_client.py -q
```

Expected: PASS.

### Task 3: Add Gateway Route

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/media.py`
- Test: `apps/openclaw-gateway/openclaw-gateway/tests/test_media_routes.py`

- [ ] **Step 1: Extend route imports**

In `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/media.py`, import:

```python
JellyseerrRequestCreate,
JellyseerrRequestResponse,
```

- [ ] **Step 2: Add real-create and validation tests**

Add tests that verify:

```python
POST /v1/media/jellyseerr/requests
```

requires auth, calls `validate_request` when `dry_run` is true, and calls `create_request` when `dry_run` is false.

- [ ] **Step 3: Implement the route**

Add:

```python
@router.post("/jellyseerr/requests")
async def jellyseerr_request(
    request: JellyseerrRequestCreate,
) -> JellyseerrRequestResponse:
    if request.dry_run:
        return await _map_upstream_errors(
            "jellyseerr",
            lambda: jellyseerr_client().validate_request(
                media_type=request.media_type,
                tmdb_id=request.tmdb_id,
            ),
        )

    return await _map_upstream_errors(
        "jellyseerr",
        lambda: jellyseerr_client().create_request(
            media_type=request.media_type,
            tmdb_id=request.tmdb_id,
        ),
    )
```

- [ ] **Step 4: Run route tests**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest tests/test_media_routes.py -q
```

Expected: PASS.

### Task 4: Document OpenClaw Usage, Confirmation, Smoke, and Rollback

**Files:**
- Modify: `apps/openclaw-gateway/README.md`
- Modify: `scripts/smoke-openclaw-gateway.sh`
- Test: `apps/openclaw-gateway/openclaw-gateway/tests/test_smoke_script.py`

- [ ] **Step 1: Add smoke-script tests for optional Jellyseerr dry-run**

Extend `tests/test_smoke_script.py` to assert that `CHECK_JELLYSEERR_REQUESTS=1` makes the script call:

```text
POST /v1/media/jellyseerr/requests
```

with a dry-run JSON payload and without printing the token.

- [ ] **Step 2: Run smoke-script tests to verify they fail**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest tests/test_smoke_script.py -q
```

Expected: FAIL because the script does not include the optional Jellyseerr request check yet.

- [ ] **Step 3: Update the smoke script**

Add optional `CHECK_JELLYSEERR_REQUESTS=1` behavior that posts:

```json
{"media_type":"movie","tmdb_id":348,"note":"OpenClaw gateway smoke dry-run","dry_run":true}
```

and accepts HTTP 200 only.

- [ ] **Step 4: Update README**

Document:

- `POST /v1/media/jellyseerr/requests` request and response examples.
- Default OpenClaw policy: use `dry_run: true` first and require explicit Oli confirmation before `dry_run: false`.
- Duplicate handling: duplicate/already-requested upstream responses return `status: "duplicate"` with `duplicate: true`.
- Secrets: OpenClaw receives only `MEDIA_GATEWAY_URL` and `MEDIA_GATEWAY_TOKEN`; Jellyseerr API key stays in Komodo/media host env.
- Rollback/disable: redeploy the previous gateway image/config through Komodo or remove the route changes and redeploy only the gateway stack through Komodo.

- [ ] **Step 5: Run smoke-script tests**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest tests/test_smoke_script.py -q
```

Expected: PASS.

### Task 5: Validate Compose and Gateway Tests

**Files:**
- No new files.

- [ ] **Step 1: Run all gateway tests**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest -q
```

Expected: PASS.

- [ ] **Step 2: Validate compose with example env**

Run:

```bash
cd apps/openclaw-gateway
docker compose --env-file example.env config >/tmp/openclaw-gateway-compose.yml
```

Expected: command exits 0 and does not deploy, pull, start, stop, or recreate containers.

- [ ] **Step 3: Review changed env references**

Run:

```bash
git diff -- apps/openclaw-gateway apps/openclaw-gateway/openclaw-gateway scripts/smoke-openclaw-gateway.sh
```

Expected: no real secrets, no `.env` values, no raw Jellyseerr passthrough, and no downloader/indexer access.

- [ ] **Step 4: Commit only with approval**

Do not commit unless Oli explicitly asks. If committing, use:

```bash
git add apps/openclaw-gateway scripts/smoke-openclaw-gateway.sh docs/superpowers/plans/2026-07-01-opn-211-jellyseerr-requests.md
git commit -m "OPN-211: add Jellyseerr request gateway endpoint"
```
