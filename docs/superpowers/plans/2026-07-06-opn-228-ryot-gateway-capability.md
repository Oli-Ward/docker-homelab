# OPN-228 Ryot Gateway Capability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a narrow Ryot capability to `openclaw-gateway` so OpenClaw can verify Ryot reachability without holding Ryot admin credentials.

**Architecture:** Keep Ryot credentials on the media host in the gateway runtime. Add a typed Ryot GraphQL client, a fixed authenticated `/v1/media/ryot/probe` route, a normalized response schema, docs, and smoke coverage. Do not expose arbitrary GraphQL passthrough or direct Ryot credentials to OpenClaw.

**Tech Stack:** Docker Compose, FastAPI, Pydantic, httpx, pytest, respx.

---

## Execution Note

During execution, upstream Ryot source was checked at `IgnisDa/ryot` commit `51d9484aa4f7455e92d22593c36a0bab793840aa`. The generated GraphQL/resolver code exposes fields such as `metadataSearch`, `metadataLookup`, `metadataDetails`, `userMetadataList`, and `userMetadataDetails`, but no single `openClawMediaState` or equivalent external-ID media-state field. All plan steps below that mention `/v1/media/ryot/media-state`, `RyotMediaStateItem`, `RyotMediaStateResponse`, or `openClawMediaState` are superseded and were intentionally not implemented. The executed slice ships only `/v1/media/ryot/probe` and documents media-state lookup as a follow-up design task.

## File Structure

- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/settings.py`
  - Add validated `ryot_url` and `ryot_admin_access_token` settings.
- Modify: `apps/openclaw-gateway/compose.yml`
  - Pass `RYOT_URL` and `RYOT_ADMIN_ACCESS_TOKEN` into the gateway container.
- Modify: `apps/openclaw-gateway/example.env`
  - Document safe placeholder values for the new required env vars.
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/media.py`
  - Add Ryot response schemas and remove the existing duplicated Jellyseerr/Jellyfin schema block while editing.
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/ryot.py`
  - Encapsulate the fixed Ryot GraphQL requests and normalization.
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/media.py`
  - Add the Ryot client factory and fixed `/v1/media/ryot/probe` route.
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_settings.py`
  - Cover the new required settings.
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_ryot_client.py`
  - Cover token use, fixed GraphQL documents, normalization, and GraphQL error handling.
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_media_routes.py`
  - Cover auth and route behavior with monkeypatched Ryot client methods.
- Modify: `apps/openclaw-gateway/README.md`
  - Document the boundary and endpoint contracts.
- Modify: `scripts/smoke-openclaw-gateway.sh`
  - Add a non-secret Ryot probe check.

### Task 1: Settings And Compose Env

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_settings.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/settings.py`
- Modify: `apps/openclaw-gateway/compose.yml`
- Modify: `apps/openclaw-gateway/example.env`

- [ ] **Step 1: Write the failing settings tests**

In `apps/openclaw-gateway/openclaw-gateway/tests/test_settings.py`, update `valid_settings_kwargs()` to include:

```python
"ryot_url": "http://ryot:8000",
"ryot_admin_access_token": "ryot-secret",
```

Add this assertion to `test_settings_accept_valid_config()`:

```python
assert str(settings.ryot_url) == "http://ryot:8000/"
assert settings.ryot_admin_access_token == "ryot-secret"
```

Add this test:

```python
def test_settings_reject_empty_ryot_admin_access_token():
    kwargs = valid_settings_kwargs()
    kwargs["ryot_admin_access_token"] = ""

    with pytest.raises(ValidationError):
        GatewaySettings(**kwargs)
```

- [ ] **Step 2: Run settings tests and verify they fail**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest tests/test_settings.py -q
```

Expected: FAIL because `GatewaySettings` does not yet define `ryot_url` and `ryot_admin_access_token`.

- [ ] **Step 3: Implement settings**

In `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/settings.py`, add these fields after `radarr_api_key`:

```python
    ryot_url: AnyHttpUrl
    ryot_admin_access_token: Annotated[str, Field(min_length=1)]
```

- [ ] **Step 4: Add compose environment wiring**

In `apps/openclaw-gateway/compose.yml`, add these lines under the existing Radarr env vars:

```yaml
      - RYOT_URL=${RYOT_URL:-http://ryot:8000}
      - RYOT_ADMIN_ACCESS_TOKEN=${RYOT_ADMIN_ACCESS_TOKEN:?Set RYOT_ADMIN_ACCESS_TOKEN in Komodo or apps/openclaw-gateway/.env}
```

In `apps/openclaw-gateway/example.env`, add:

```text
RYOT_URL=http://ryot:8000
RYOT_ADMIN_ACCESS_TOKEN=change-me
```

- [ ] **Step 5: Run settings and compose validation**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest tests/test_settings.py -q
```

Expected: PASS.

Run:

```bash
docker compose --env-file apps/openclaw-gateway/example.env -f apps/openclaw-gateway/compose.yml config >/tmp/opn-228-openclaw-gateway-compose.yml
```

Expected: exit 0; do not deploy or restart anything.

### Task 2: Ryot Schemas

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/media.py`

- [ ] **Step 1: Add Ryot schemas**

In `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/media.py`, add:

```python
class RyotProbeResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["ryot"]
    typename: str


class RyotMediaStateItem(BaseModel):
    id: str
    title: str
    media_type: Literal["movie", "tv", "unknown"]
    year: int | None = None
    imdb_id: str | None = None
    tmdb_id: int | None = None
    tvdb_id: int | None = None
    watched: bool
    watchlist: bool
    rating: int | None = None


class RyotMediaStateResponse(BaseModel):
    items: list[RyotMediaStateItem]
```

While editing this file, remove the duplicated second definitions of `JellyseerrRequestCreate`, `JellyseerrRequestResponse`, `JellyfinWatchCompletedEvent`, and `JellyfinWatchCompletedResponse`. Keep one definition of each.

- [ ] **Step 2: Run import check**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m py_compile openclaw_gateway/schemas/media.py
```

Expected: exit 0.

### Task 3: Ryot Client

**Files:**
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/ryot.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_ryot_client.py`

- [ ] **Step 1: Write failing client tests**

Create `apps/openclaw-gateway/openclaw-gateway/tests/test_ryot_client.py` with:

```python
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
    assert request.json()["query"] == "query OpenClawRyotProbe { __typename }"
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
async def test_ryot_media_state_normalizes_items():
    route = respx.post("http://ryot:8000/backend/graphql").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "items": [
                        {
                            "id": "ryot-1",
                            "title": "The Matrix",
                            "mediaType": "movie",
                            "year": 1999,
                            "imdbId": "tt0133093",
                            "tmdbId": 603,
                            "tvdbId": None,
                            "watched": True,
                            "watchlist": False,
                            "rating": 90,
                        }
                    ]
                }
            },
        )
    )
    client = RyotClient(
        base_url="http://ryot:8000",
        admin_access_token="ryot-secret",
        timeout_seconds=5.0,
    )

    result = await client.media_state(external_source="imdb", external_id="tt0133093")

    assert route.called
    request_payload = route.calls.last.request.json()
    assert request_payload["variables"] == {
        "externalSource": "imdb",
        "externalId": "tt0133093",
    }
    assert result.items[0].id == "ryot-1"
    assert result.items[0].title == "The Matrix"
    assert result.items[0].media_type == "movie"
    assert result.items[0].imdb_id == "tt0133093"
    assert result.items[0].tmdb_id == 603
    assert result.items[0].watched is True
    assert result.items[0].watchlist is False
    assert result.items[0].rating == 90
```

- [ ] **Step 2: Run client tests and verify they fail**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest tests/test_ryot_client.py -q
```

Expected: FAIL because `openclaw_gateway.clients.ryot` does not exist.

- [ ] **Step 3: Implement the client**

Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/ryot.py`:

```python
import httpx

from openclaw_gateway.schemas.media import (
    RyotMediaStateItem,
    RyotMediaStateResponse,
    RyotProbeResponse,
)


class RyotGraphQLError(Exception):
    pass


class RyotClient:
    def __init__(self, base_url: str, admin_access_token: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._admin_access_token = admin_access_token
        self._timeout = httpx.Timeout(timeout_seconds)

    async def probe(self) -> RyotProbeResponse:
        payload = await self._graphql(
            query="query OpenClawRyotProbe { __typename }",
            variables={},
        )
        return RyotProbeResponse(
            status="ok",
            service="ryot",
            typename=str(payload.get("__typename", "")),
        )

    async def media_state(self, external_source: str, external_id: str) -> RyotMediaStateResponse:
        payload = await self._graphql(
            query=(
                "query OpenClawRyotMediaState($externalSource: String!, $externalId: String!) "
                "{ items: openClawMediaState(externalSource: $externalSource, externalId: $externalId) "
                "{ id title mediaType year imdbId tmdbId tvdbId watched watchlist rating } }"
            ),
            variables={"externalSource": external_source, "externalId": external_id},
        )
        items = [self._normalize_item(item) for item in payload.get("items", [])]
        return RyotMediaStateResponse(items=items)

    async def _graphql(self, query: str, variables: dict) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/backend/graphql",
                headers={
                    "Authorization": f"Bearer {self._admin_access_token}",
                    "Content-Type": "application/json",
                },
                json={"query": query, "variables": variables},
            )
            response.raise_for_status()

        payload = response.json()
        if payload.get("errors"):
            raise RyotGraphQLError("ryot graphql error")

        data = payload.get("data")
        if not isinstance(data, dict):
            raise RyotGraphQLError("ryot graphql response missing data")

        return data

    def _normalize_item(self, item: dict) -> RyotMediaStateItem:
        media_type = str(item.get("mediaType") or "unknown").lower()
        if media_type not in {"movie", "tv"}:
            media_type = "unknown"

        return RyotMediaStateItem(
            id=str(item.get("id", "")),
            title=str(item.get("title", "")),
            media_type=media_type,
            year=item.get("year"),
            imdb_id=item.get("imdbId"),
            tmdb_id=item.get("tmdbId"),
            tvdb_id=item.get("tvdbId"),
            watched=bool(item.get("watched", False)),
            watchlist=bool(item.get("watchlist", False)),
            rating=item.get("rating"),
        )
```

Important implementation note: `openClawMediaState` is the intended normalized query shape for this plan. Before merging, verify Ryot v10's actual GraphQL schema. If this exact field does not exist, replace the query and test fixture with the real field path or keep only the `/probe` endpoint and document the schema blocker in Linear.

- [ ] **Step 4: Run client tests**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest tests/test_ryot_client.py -q
```

Expected: PASS after the real Ryot schema-backed query is implemented. If schema verification invalidates the planned lookup query, keep the probe tests passing and update the media-state test to the verified query before proceeding.

### Task 4: Gateway Routes

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/media.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_media_routes.py`

- [ ] **Step 1: Write failing route tests**

In `apps/openclaw-gateway/openclaw-gateway/tests/test_media_routes.py`, import:

```python
from openclaw_gateway.schemas.media import (
    RyotMediaStateItem,
    RyotMediaStateResponse,
    RyotProbeResponse,
)
```

Update `make_settings()` to pass:

```python
ryot_url="http://ryot:8000",
ryot_admin_access_token="ryot-secret",
```

Add these tests:

```python
@pytest.mark.asyncio
async def test_ryot_probe_route_requires_auth():
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/media/ryot/probe")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ryot_probe_route_returns_normalized_status(monkeypatch):
    async def probe(self):
        return RyotProbeResponse(status="ok", service="ryot", typename="QueryRoot")

    monkeypatch.setattr("openclaw_gateway.routers.media.RyotClient.probe", probe)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/media/ryot/probe",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ryot",
        "typename": "QueryRoot",
    }


@pytest.mark.asyncio
async def test_ryot_media_state_route_returns_normalized_items(monkeypatch):
    async def media_state(self, external_source: str, external_id: str):
        assert external_source == "imdb"
        assert external_id == "tt0133093"
        return RyotMediaStateResponse(
            items=[
                RyotMediaStateItem(
                    id="ryot-1",
                    title="The Matrix",
                    media_type="movie",
                    year=1999,
                    imdb_id="tt0133093",
                    tmdb_id=603,
                    tvdb_id=None,
                    watched=True,
                    watchlist=False,
                    rating=90,
                )
            ]
        )

    monkeypatch.setattr("openclaw_gateway.routers.media.RyotClient.media_state", media_state)
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/media/ryot/media-state?external_source=imdb&external_id=tt0133093",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 200
    assert response.json()["items"][0]["title"] == "The Matrix"
    assert response.json()["items"][0]["watched"] is True


@pytest.mark.asyncio
async def test_ryot_media_state_route_rejects_unknown_external_source():
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/media/ryot/media-state?external_source=letterboxd&external_id=abc",
            headers={"Authorization": "Bearer gateway-secret"},
        )

    assert response.status_code == 422
```

- [ ] **Step 2: Run route tests and verify they fail**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest tests/test_media_routes.py -q
```

Expected: FAIL because `RyotClient` and the routes do not exist.

- [ ] **Step 3: Implement routes**

In `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/media.py`, import:

```python
from typing import Literal, TypeVar
```

Replace the existing `from typing import TypeVar` import with the combined import above.

Import the client:

```python
from openclaw_gateway.clients.ryot import RyotClient, RyotGraphQLError
```

Import schemas:

```python
    RyotMediaStateResponse,
    RyotProbeResponse,
```

Add `RyotGraphQLError` handling to `_map_upstream_errors` before the generic `httpx.HTTPError` block:

```python
    except RyotGraphQLError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{upstream_name} graphql error",
        ) from exc
```

Add the client factory inside `build_media_router()`:

```python
    def ryot_client() -> RyotClient:
        return RyotClient(
            base_url=str(settings.ryot_url),
            admin_access_token=settings.ryot_admin_access_token,
            timeout_seconds=settings.upstream_timeout_seconds,
        )
```

Add routes before the Sonarr route:

```python
    @router.get("/ryot/probe")
    async def ryot_probe() -> RyotProbeResponse:
        return await _map_upstream_errors("ryot", ryot_client().probe)

    @router.get("/ryot/media-state")
    async def ryot_media_state(
        external_source: Literal["imdb", "tmdb", "tvdb"],
        external_id: str = Query(min_length=1),
    ) -> RyotMediaStateResponse:
        return await _map_upstream_errors(
            "ryot",
            lambda: ryot_client().media_state(
                external_source=external_source,
                external_id=external_id,
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

### Task 5: Documentation And Smoke Script

**Files:**
- Modify: `apps/openclaw-gateway/README.md`
- Modify: `scripts/smoke-openclaw-gateway.sh`

- [ ] **Step 1: Update README endpoint list**

In `apps/openclaw-gateway/README.md`, add these endpoints to the endpoint block:

```text
GET /v1/media/ryot/probe
GET /v1/media/ryot/media-state?external_source=imdb&external_id=...
```

Add this boundary text near the existing “Do not give OpenClaw...” paragraph:

```markdown
Do not give OpenClaw `RYOT_ADMIN_ACCESS_TOKEN`. Ryot admin access belongs in the gateway runtime only. OpenClaw should call the fixed Ryot gateway endpoints with the same gateway bearer token it already uses for Jellyfin, Jellyseerr, Sonarr, and Radarr.
```

Add the probe response example:

```json
{
  "status": "ok",
  "service": "ryot",
  "typename": "QueryRoot"
}
```

Add the media-state response example from the spec.

- [ ] **Step 2: Add smoke script probe**

In `scripts/smoke-openclaw-gateway.sh`, after an authenticated existing read-only check, add:

```bash
ryot_probe_status="$(curl -sS -o /tmp/openclaw-gateway-ryot-probe.json -w "%{http_code}" \
  -H "Authorization: Bearer ${gateway_token}" \
  "${gateway_url%/}/v1/media/ryot/probe")"

if [[ "${ryot_probe_status}" != "200" ]]; then
  echo "Ryot probe failed with HTTP ${ryot_probe_status}." >&2
  exit 1
fi
```

Do not echo the token. Do not print the saved JSON file by default.

- [ ] **Step 3: Validate docs and shell syntax**

Run:

```bash
bash -n scripts/smoke-openclaw-gateway.sh
```

Expected: exit 0.

Run:

```bash
rg -n "RYOT_ADMIN_ACCESS_TOKEN|/v1/media/ryot|raw GraphQL|passthrough" apps/openclaw-gateway/README.md scripts/smoke-openclaw-gateway.sh
```

Expected: matches show the new endpoint docs and no instruction to give Ryot admin credentials to OpenClaw.

### Task 6: Full Verification And Linear Update

**Files:**
- Verify all changed files.
- Update Linear OPN-228 with results.

- [ ] **Step 1: Run full gateway tests**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest -q
```

Expected: PASS.

- [ ] **Step 2: Run compose config validation**

Run:

```bash
docker compose --env-file apps/openclaw-gateway/example.env -f apps/openclaw-gateway/compose.yml config >/tmp/opn-228-openclaw-gateway-compose.yml
```

Expected: exit 0.

- [ ] **Step 3: Run shell validation**

Run:

```bash
bash -n scripts/smoke-openclaw-gateway.sh
```

Expected: exit 0.

- [ ] **Step 4: Review for secret leakage**

Run:

```bash
git diff -- apps/openclaw-gateway scripts/smoke-openclaw-gateway.sh docs/superpowers/specs/2026-07-06-opn-228-ryot-gateway-design.md docs/superpowers/plans/2026-07-06-opn-228-ryot-gateway-capability.md
```

Expected: diff contains only placeholder values like `change-me`; no real tokens, cookies, private keys, `.env` contents, logs, or runtime state.

- [ ] **Step 5: Update Linear**

Add a Linear comment to OPN-228:

```markdown
Gateway-side Ryot unblock work is ready for deployment review.

What changed:
- Added narrow Ryot gateway capability under `/v1/media/ryot/...`.
- Kept `RYOT_ADMIN_ACCESS_TOKEN` on the media-host gateway runtime boundary.
- OpenClaw should continue to use `MEDIA_GATEWAY_URL` and `MEDIA_GATEWAY_TOKEN`.

Verification:
- `pytest -q` in `apps/openclaw-gateway/openclaw-gateway`: PASS
- `docker compose --env-file apps/openclaw-gateway/example.env -f apps/openclaw-gateway/compose.yml config`: PASS
- `bash -n scripts/smoke-openclaw-gateway.sh`: PASS

Remaining external work:
- Add `RYOT_URL` and `RYOT_ADMIN_ACCESS_TOKEN` to the openclaw-gateway Komodo env.
- Redeploy openclaw-gateway through Komodo.
- Update OpenClaw's Ryot probe to call the gateway endpoint instead of direct Ryot env vars.
- Run live smoke verification without printing token values.
```

Keep OPN-228 blocked until the gateway stack has been deployed through Komodo and the OpenClaw probe has been updated or rerun successfully against the gateway.

## Final Self-Review

- Spec coverage: Tasks cover settings, compose env, schemas, client, routes, docs, smoke validation, and Linear update.
- Placeholder scan: The plan uses only placeholder secret values and explicitly forbids real token output.
- Type consistency: `RyotProbeResponse`, `RyotMediaStateItem`, and `RyotMediaStateResponse` are defined before route/client usage.
- Risk note: The planned `media_state` GraphQL query must be verified against Ryot v10 before merge. If the schema does not support it, ship only `/probe` and document the exact Ryot schema blocker.
