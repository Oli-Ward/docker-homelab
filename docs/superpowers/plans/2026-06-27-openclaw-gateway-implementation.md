# OpenClaw Gateway Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `apps/openclaw-gateway`, a Dockerized FastAPI gateway exposing read-only Jellyfin and Jellyseerr capability endpoints to OpenClaw through a token-protected API.

**Architecture:** Create a new independent Compose stack with a small FastAPI app under `apps/openclaw-gateway/openclaw-gateway`. The app validates gateway/upstream config at startup, requires bearer auth for `/v1/...`, calls Jellyfin and Jellyseerr over `media_net`, normalizes upstream payloads, and documents the operational boundary.

**Tech Stack:** Docker Compose, Python 3.12, FastAPI, Uvicorn, Pydantic Settings, HTTPX, pytest, respx, shell/curl smoke test.

---

## Source Documents

- Spec: `docs/superpowers/specs/2026-06-27-openclaw-gateway-design.md`
- Linear: `OPN-153`
- Deferred Sonarr/Radarr follow-up: `OPN-156`

## File Map

- Create `apps/openclaw-gateway/compose.yml`: Compose stack, LAN-bound port, `media_net` only.
- Create `apps/openclaw-gateway/example.env`: documented placeholder env vars, no real secrets.
- Create `apps/openclaw-gateway/README.md`: runbook, network boundary, endpoints, firewall guidance, smoke-test usage.
- Create `apps/openclaw-gateway/openclaw-gateway/Dockerfile`: production image for FastAPI app.
- Create `apps/openclaw-gateway/openclaw-gateway/pyproject.toml`: Python package metadata and dependencies.
- Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/__init__.py`: package marker.
- Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/main.py`: FastAPI app factory, health route, router registration.
- Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/settings.py`: Pydantic settings, fail-fast validation.
- Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/auth.py`: bearer-token dependency.
- Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/jellyfin.py`: Jellyfin API client and normalization.
- Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/jellyseerr.py`: Jellyseerr API client and normalization.
- Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/media.py`: `/v1/media/...` routes and error mapping.
- Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/media.py`: response models.
- Create `apps/openclaw-gateway/openclaw-gateway/tests/`: pytest coverage for settings, auth, clients, and routes.
- Create `scripts/smoke-openclaw-gateway.sh`: health and authenticated search smoke test.

## Implementation Tasks

### Task 1: Python Project Skeleton and Health Route

**Files:**
- Create: `apps/openclaw-gateway/openclaw-gateway/pyproject.toml`
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/__init__.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/main.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_health.py`

- [ ] **Step 1: Write the failing health test**

Create `apps/openclaw-gateway/openclaw-gateway/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from openclaw_gateway.main import create_app


def test_health_is_public():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Add project metadata and dependencies**

Create `apps/openclaw-gateway/openclaw-gateway/pyproject.toml`:

```toml
[project]
name = "openclaw-gateway"
version = "0.1.0"
description = "Internal OpenClaw capability gateway for selected homelab APIs"
requires-python = ">=3.12"
dependencies = [
  "fastapi==0.115.6",
  "httpx==0.28.1",
  "pydantic-settings==2.7.1",
  "uvicorn[standard]==0.34.0",
]

[project.optional-dependencies]
test = [
  "pytest==8.3.4",
  "pytest-asyncio==0.25.2",
  "respx==0.22.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 3: Install test dependencies locally**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pip install -e ".[test]"
```

Expected: dependencies install successfully, including FastAPI, HTTPX, pytest, pytest-asyncio, and respx.

- [ ] **Step 4: Add the minimal app implementation**

Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/__init__.py`:

```python
"""OpenClaw internal capability gateway."""
```

Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/main.py`:

```python
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="OpenClaw Gateway", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 5: Run the health test**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_health.py -v
```

Expected: `test_health_is_public` passes.

- [ ] **Step 6: Commit**

```bash
git add apps/openclaw-gateway/openclaw-gateway/pyproject.toml apps/openclaw-gateway/openclaw-gateway/openclaw_gateway apps/openclaw-gateway/openclaw-gateway/tests/test_health.py
git commit -m "OPN-153: scaffold OpenClaw gateway app"
```

### Task 2: Settings Validation and Bearer Auth

**Files:**
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/settings.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/auth.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_settings.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_auth.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/main.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_health.py`

- [ ] **Step 1: Write failing settings tests**

Create `apps/openclaw-gateway/openclaw-gateway/tests/test_settings.py`:

```python
import pytest
from pydantic import ValidationError

from openclaw_gateway.settings import GatewaySettings


def valid_settings_kwargs() -> dict[str, str | float]:
    return {
        "gateway_auth_token": "gateway-secret",
        "jellyfin_url": "http://jellyfin:8096",
        "jellyfin_api_key": "jellyfin-secret",
        "jellyseerr_url": "http://jellyseerr:5055",
        "jellyseerr_api_key": "jellyseerr-secret",
        "upstream_timeout_seconds": 5.0,
    }


def test_settings_accept_valid_config():
    settings = GatewaySettings(**valid_settings_kwargs())

    assert settings.gateway_auth_token == "gateway-secret"
    assert str(settings.jellyfin_url) == "http://jellyfin:8096/"
    assert str(settings.jellyseerr_url) == "http://jellyseerr:5055/"
    assert settings.upstream_timeout_seconds == 5.0


def test_settings_reject_missing_gateway_token():
    kwargs = valid_settings_kwargs()
    kwargs["gateway_auth_token"] = ""

    with pytest.raises(ValidationError):
        GatewaySettings(**kwargs)
```

- [ ] **Step 2: Write failing auth tests**

Create `apps/openclaw-gateway/openclaw-gateway/tests/test_auth.py`:

```python
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from openclaw_gateway.auth import require_gateway_token
from openclaw_gateway.settings import GatewaySettings


def make_client() -> TestClient:
    settings = GatewaySettings(
        gateway_auth_token="gateway-secret",
        jellyfin_url="http://jellyfin:8096",
        jellyfin_api_key="jellyfin-secret",
        jellyseerr_url="http://jellyseerr:5055",
        jellyseerr_api_key="jellyseerr-secret",
        upstream_timeout_seconds=5.0,
    )
    app = FastAPI()

    @app.get("/protected", dependencies=[Depends(require_gateway_token(settings))])
    def protected() -> dict[str, str]:
        return {"ok": "true"}

    return TestClient(app)


def test_missing_bearer_token_is_unauthorized():
    response = make_client().get("/protected")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"


def test_invalid_bearer_token_is_unauthorized():
    response = make_client().get(
        "/protected",
        headers={"Authorization": "Bearer wrong-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid bearer token"


def test_valid_bearer_token_is_allowed():
    response = make_client().get(
        "/protected",
        headers={"Authorization": "Bearer gateway-secret"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": "true"}
```

- [ ] **Step 3: Implement settings and auth**

Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/settings.py`:

```python
from functools import lru_cache
from typing import Annotated

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gateway_auth_token: Annotated[str, Field(min_length=1)]
    jellyfin_url: AnyHttpUrl
    jellyfin_api_key: Annotated[str, Field(min_length=1)]
    jellyseerr_url: AnyHttpUrl
    jellyseerr_api_key: Annotated[str, Field(min_length=1)]
    upstream_timeout_seconds: Annotated[float, Field(gt=0)] = 5.0


@lru_cache
def get_settings() -> GatewaySettings:
    return GatewaySettings()
```

Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/auth.py`:

```python
from collections.abc import Callable
from secrets import compare_digest

from fastapi import Header, HTTPException, status

from openclaw_gateway.settings import GatewaySettings


def require_gateway_token(settings: GatewaySettings) -> Callable[[str | None], None]:
    def dependency(authorization: str | None = Header(default=None)) -> None:
        if authorization is None or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
            )

        supplied_token = authorization.removeprefix("Bearer ").strip()
        if not compare_digest(supplied_token, settings.gateway_auth_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid bearer token",
            )

    return dependency
```

- [ ] **Step 4: Update the health test to pass explicit test settings**

Modify `apps/openclaw-gateway/openclaw-gateway/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from openclaw_gateway.main import create_app
from openclaw_gateway.settings import GatewaySettings


def test_health_is_public():
    settings = GatewaySettings(
        gateway_auth_token="gateway-secret",
        jellyfin_url="http://jellyfin:8096",
        jellyfin_api_key="jellyfin-secret",
        jellyseerr_url="http://jellyseerr:5055",
        jellyseerr_api_key="jellyseerr-secret",
        upstream_timeout_seconds=5.0,
    )
    client = TestClient(create_app(settings=settings))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 5: Wire settings into app startup**

Modify `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/main.py`:

```python
from fastapi import FastAPI

from openclaw_gateway.settings import GatewaySettings, get_settings


def create_app(settings: GatewaySettings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    app = FastAPI(title="OpenClaw Gateway", version="0.1.0")
    app.state.settings = app_settings

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 6: Run settings, auth, and health tests**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_settings.py tests/test_auth.py tests/test_health.py -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/settings.py apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/auth.py apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/main.py apps/openclaw-gateway/openclaw-gateway/tests/test_settings.py apps/openclaw-gateway/openclaw-gateway/tests/test_auth.py apps/openclaw-gateway/openclaw-gateway/tests/test_health.py
git commit -m "OPN-153: add gateway config and bearer auth"
```

### Task 3: Media Schemas and Jellyfin Client

**Files:**
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/__init__.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/media.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/__init__.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/jellyfin.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_jellyfin_client.py`

- [ ] **Step 1: Write failing Jellyfin normalization tests**

Create `apps/openclaw-gateway/openclaw-gateway/tests/test_jellyfin_client.py`:

```python
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
```

- [ ] **Step 2: Add schemas**

Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/__init__.py`:

```python
"""Response schemas for normalized gateway APIs."""
```

Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/media.py`:

```python
from pydantic import BaseModel


class MediaItem(BaseModel):
    id: str
    type: str
    title: str
    year: int | None = None
    overview: str | None = None
    available: bool
    request_status: str | None = None


class MediaSearchResponse(BaseModel):
    items: list[MediaItem]
```

- [ ] **Step 3: Implement the Jellyfin client**

Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/__init__.py`:

```python
"""Upstream API clients."""
```

Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/jellyfin.py`:

```python
import httpx

from openclaw_gateway.schemas.media import MediaItem, MediaSearchResponse


class JellyfinClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = httpx.Timeout(timeout_seconds)

    async def library(self) -> MediaSearchResponse:
        return await self._items(params={"Recursive": "true", "IncludeItemTypes": "Movie,Series"})

    async def search(self, query: str) -> MediaSearchResponse:
        return await self._items(
            params={
                "Recursive": "true",
                "SearchTerm": query,
                "IncludeItemTypes": "Movie,Series",
            }
        )

    async def _items(self, params: dict[str, str]) -> MediaSearchResponse:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}/Items",
                headers={"X-Emby-Token": self._api_key},
                params=params,
            )
            response.raise_for_status()

        items = [self._normalize_item(item) for item in response.json().get("Items", [])]
        return MediaSearchResponse(items=items)

    def _normalize_item(self, item: dict) -> MediaItem:
        return MediaItem(
            id=str(item.get("Id", "")),
            type=str(item.get("Type", "unknown")).lower(),
            title=str(item.get("Name", "")),
            year=item.get("ProductionYear"),
            overview=item.get("Overview"),
            available=True,
        )
```

- [ ] **Step 4: Run Jellyfin tests**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_jellyfin_client.py -v
```

Expected: both Jellyfin tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients apps/openclaw-gateway/openclaw-gateway/tests/test_jellyfin_client.py
git commit -m "OPN-153: add normalized Jellyfin client"
```

### Task 4: Jellyseerr Client

**Files:**
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/jellyseerr.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_jellyseerr_client.py`

- [ ] **Step 1: Write failing Jellyseerr normalization test**

Create `apps/openclaw-gateway/openclaw-gateway/tests/test_jellyseerr_client.py`:

```python
import httpx
import pytest
import respx

from openclaw_gateway.clients.jellyseerr import JellyseerrClient


@pytest.mark.asyncio
@respx.mock
async def test_jellyseerr_search_normalizes_results():
    route = respx.get("http://jellyseerr:5055/api/v1/search").mock(
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
    client = JellyseerrClient(
        base_url="http://jellyseerr:5055",
        api_key="jellyseerr-secret",
        timeout_seconds=5.0,
    )

    result = await client.search("alien")

    assert route.called
    assert result.items[0].id == "348"
    assert result.items[0].type == "movie"
    assert result.items[0].title == "Alien"
    assert result.items[0].year == 1979
    assert result.items[0].overview == "Space horror"
    assert result.items[0].available is True
    assert result.items[0].request_status == "approved"
```

- [ ] **Step 2: Implement the Jellyseerr client**

Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/jellyseerr.py`:

```python
import httpx

from openclaw_gateway.schemas.media import MediaItem, MediaSearchResponse


JELLYSEERR_AVAILABLE_STATUS = 5
REQUEST_STATUS_LABELS = {
    1: "pending",
    2: "approved",
    3: "declined",
}


class JellyseerrClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = httpx.Timeout(timeout_seconds)

    async def search(self, query: str) -> MediaSearchResponse:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}/api/v1/search",
                headers={"X-Api-Key": self._api_key},
                params={"query": query},
            )
            response.raise_for_status()

        items = [self._normalize_item(item) for item in response.json().get("results", [])]
        return MediaSearchResponse(items=items)

    def _normalize_item(self, item: dict) -> MediaItem:
        media_info = item.get("mediaInfo") or {}
        requests = media_info.get("requests") or []
        request_status = None
        if requests:
            request_status = REQUEST_STATUS_LABELS.get(requests[0].get("status"), "unknown")

        title = item.get("title") or item.get("name") or item.get("originalTitle") or ""
        release_date = item.get("releaseDate") or item.get("firstAirDate") or ""
        year = int(release_date[:4]) if len(release_date) >= 4 and release_date[:4].isdigit() else None

        return MediaItem(
            id=str(item.get("id", "")),
            type=str(item.get("mediaType", "unknown")).lower(),
            title=str(title),
            year=year,
            overview=item.get("overview"),
            available=media_info.get("status") == JELLYSEERR_AVAILABLE_STATUS,
            request_status=request_status,
        )
```

- [ ] **Step 3: Run Jellyseerr tests**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_jellyseerr_client.py -v
```

Expected: Jellyseerr normalization test passes.

- [ ] **Step 4: Commit**

```bash
git add apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/jellyseerr.py apps/openclaw-gateway/openclaw-gateway/tests/test_jellyseerr_client.py
git commit -m "OPN-153: add normalized Jellyseerr client"
```

### Task 5: Media Routes and Upstream Error Mapping

**Files:**
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/__init__.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/media.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_media_routes.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/main.py`

- [ ] **Step 1: Write failing route tests**

Create `apps/openclaw-gateway/openclaw-gateway/tests/test_media_routes.py`:

```python
from fastapi.testclient import TestClient

from openclaw_gateway.main import create_app
from openclaw_gateway.settings import GatewaySettings


def make_client() -> TestClient:
    settings = GatewaySettings(
        gateway_auth_token="gateway-secret",
        jellyfin_url="http://jellyfin:8096",
        jellyfin_api_key="jellyfin-secret",
        jellyseerr_url="http://jellyseerr:5055",
        jellyseerr_api_key="jellyseerr-secret",
        upstream_timeout_seconds=5.0,
    )
    return TestClient(create_app(settings=settings))


def test_media_routes_require_auth():
    response = make_client().get("/v1/media/jellyfin/search?q=alien")

    assert response.status_code == 401


def test_jellyfin_search_route_returns_normalized_items(monkeypatch):
    async def fake_search(self, query):
        from openclaw_gateway.schemas.media import MediaItem, MediaSearchResponse

        assert query == "alien"
        return MediaSearchResponse(
            items=[
                MediaItem(
                    id="abc",
                    type="movie",
                    title="Alien",
                    year=1979,
                    overview="Space horror",
                    available=True,
                )
            ]
        )

    monkeypatch.setattr("openclaw_gateway.clients.jellyfin.JellyfinClient.search", fake_search)

    response = make_client().get(
        "/v1/media/jellyfin/search?q=alien",
        headers={"Authorization": "Bearer gateway-secret"},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["title"] == "Alien"


def test_jellyseerr_search_route_returns_normalized_items(monkeypatch):
    async def fake_search(self, query):
        from openclaw_gateway.schemas.media import MediaItem, MediaSearchResponse

        assert query == "alien"
        return MediaSearchResponse(
            items=[
                MediaItem(
                    id="348",
                    type="movie",
                    title="Alien",
                    year=1979,
                    overview="Space horror",
                    available=True,
                    request_status="approved",
                )
            ]
        )

    monkeypatch.setattr("openclaw_gateway.clients.jellyseerr.JellyseerrClient.search", fake_search)

    response = make_client().get(
        "/v1/media/jellyseerr/search?q=alien",
        headers={"Authorization": "Bearer gateway-secret"},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["request_status"] == "approved"
```

- [ ] **Step 2: Implement media router**

Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/__init__.py`:

```python
"""HTTP routers for gateway capabilities."""
```

Create `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/media.py`:

```python
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status

from openclaw_gateway.auth import require_gateway_token
from openclaw_gateway.clients.jellyfin import JellyfinClient
from openclaw_gateway.clients.jellyseerr import JellyseerrClient
from openclaw_gateway.schemas.media import MediaSearchResponse
from openclaw_gateway.settings import GatewaySettings


def build_media_router(settings: GatewaySettings) -> APIRouter:
    router = APIRouter(
        prefix="/v1/media",
        dependencies=[Depends(require_gateway_token(settings))],
    )

    @router.get("/jellyfin/library", response_model=MediaSearchResponse)
    async def jellyfin_library(request: Request) -> MediaSearchResponse:
        client = JellyfinClient(
            base_url=str(settings.jellyfin_url),
            api_key=settings.jellyfin_api_key,
            timeout_seconds=settings.upstream_timeout_seconds,
        )
        return await _call_upstream("jellyfin", client.library)

    @router.get("/jellyfin/search", response_model=MediaSearchResponse)
    async def jellyfin_search(q: str) -> MediaSearchResponse:
        client = JellyfinClient(
            base_url=str(settings.jellyfin_url),
            api_key=settings.jellyfin_api_key,
            timeout_seconds=settings.upstream_timeout_seconds,
        )
        return await _call_upstream("jellyfin", lambda: client.search(q))

    @router.get("/jellyseerr/search", response_model=MediaSearchResponse)
    async def jellyseerr_search(q: str) -> MediaSearchResponse:
        client = JellyseerrClient(
            base_url=str(settings.jellyseerr_url),
            api_key=settings.jellyseerr_api_key,
            timeout_seconds=settings.upstream_timeout_seconds,
        )
        return await _call_upstream("jellyseerr", lambda: client.search(q))

    return router


async def _call_upstream(upstream: str, call):
    try:
        return await call()
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"{upstream} timed out",
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{upstream} returned {exc.response.status_code}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{upstream} request failed",
        ) from exc
```

- [ ] **Step 3: Register router in app factory**

Modify `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/main.py`:

```python
from fastapi import FastAPI

from openclaw_gateway.routers.media import build_media_router
from openclaw_gateway.settings import GatewaySettings, get_settings


def create_app(settings: GatewaySettings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    app = FastAPI(title="OpenClaw Gateway", version="0.1.0")
    app.state.settings = app_settings
    app.include_router(build_media_router(app_settings))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 4: Run route tests**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_media_routes.py -v
```

Expected: all media route tests pass.

- [ ] **Step 5: Run the full app test suite**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/main.py apps/openclaw-gateway/openclaw-gateway/tests/test_media_routes.py
git commit -m "OPN-153: expose authenticated media routes"
```

### Task 6: Docker, Compose, and Example Environment

**Files:**
- Create: `apps/openclaw-gateway/compose.yml`
- Create: `apps/openclaw-gateway/example.env`
- Create: `apps/openclaw-gateway/openclaw-gateway/Dockerfile`

- [ ] **Step 1: Add Dockerfile**

Create `apps/openclaw-gateway/openclaw-gateway/Dockerfile`:

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir "."

COPY openclaw_gateway /app/openclaw_gateway

EXPOSE 8080

CMD ["uvicorn", "openclaw_gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 2: Add Compose stack**

Create `apps/openclaw-gateway/compose.yml`:

```yaml
services:
  openclaw-gateway:
    build: ./openclaw-gateway
    container_name: openclaw-gateway
    restart: unless-stopped
    ports:
      - "${GATEWAY_BIND_HOST}:${GATEWAY_PORT:-8088}:8080"
    environment:
      - GATEWAY_AUTH_TOKEN=${GATEWAY_AUTH_TOKEN}
      - JELLYFIN_URL=${JELLYFIN_URL}
      - JELLYFIN_API_KEY=${JELLYFIN_API_KEY}
      - JELLYSEERR_URL=${JELLYSEERR_URL}
      - JELLYSEERR_API_KEY=${JELLYSEERR_API_KEY}
      - UPSTREAM_TIMEOUT_SECONDS=${UPSTREAM_TIMEOUT_SECONDS:-5}
    networks:
      - media_net

networks:
  media_net:
    external: true
```

- [ ] **Step 3: Add example env with placeholders only**

Create `apps/openclaw-gateway/example.env`:

```dotenv
GATEWAY_BIND_HOST=192.168.1.103
GATEWAY_PORT=8088
GATEWAY_AUTH_TOKEN=change-me
JELLYFIN_URL=http://jellyfin:8096
JELLYFIN_API_KEY=change-me
JELLYSEERR_URL=http://jellyseerr:5055
JELLYSEERR_API_KEY=change-me
UPSTREAM_TIMEOUT_SECONDS=5
```

- [ ] **Step 4: Validate Compose syntax**

Run:

```bash
docker compose --env-file apps/openclaw-gateway/example.env -f apps/openclaw-gateway/compose.yml config
```

Expected: Compose renders one `openclaw-gateway` service, one external `media_net`, and no `proxy_net`, Docker socket mount, host networking, or media volume mounts.

- [ ] **Step 5: Commit**

```bash
git add apps/openclaw-gateway/compose.yml apps/openclaw-gateway/example.env apps/openclaw-gateway/openclaw-gateway/Dockerfile
git commit -m "OPN-153: add gateway Docker stack"
```

### Task 7: Runbook and Smoke Test

**Files:**
- Create: `apps/openclaw-gateway/README.md`
- Create: `scripts/smoke-openclaw-gateway.sh`

- [ ] **Step 1: Add gateway runbook**

Create `apps/openclaw-gateway/README.md`:

```markdown
# OpenClaw Gateway

Dockerized FastAPI gateway for selected OpenClaw homelab capabilities.

## Boundary

OpenClaw calls this gateway over the media host LAN IP. The gateway calls upstream services over Docker networks and keeps upstream API keys on the media host.

For OPN-153, the gateway exposes only read-only Jellyfin and Jellyseerr media endpoints. It does not expose Sonarr, Radarr, qBittorrent, NZBGet, Prowlarr, Docker logs, Paperless, n8n, raw passthrough routes, the Docker socket, host networking, or media filesystem mounts.

## Endpoints

```text
GET /health
GET /v1/media/jellyfin/library
GET /v1/media/jellyfin/search?q=...
GET /v1/media/jellyseerr/search?q=...
```

`/health` is public and returns only `{ "status": "ok" }`.

All `/v1/...` endpoints require:

```text
Authorization: Bearer <token>
```

## Environment

Copy `example.env` to `.env` in Komodo or the deployment environment and replace placeholder values.

```dotenv
GATEWAY_BIND_HOST=192.168.1.103
GATEWAY_PORT=8088
GATEWAY_AUTH_TOKEN=change-me
JELLYFIN_URL=http://jellyfin:8096
JELLYFIN_API_KEY=change-me
JELLYSEERR_URL=http://jellyseerr:5055
JELLYSEERR_API_KEY=change-me
UPSTREAM_TIMEOUT_SECONDS=5
```

Do not commit `.env` or real API keys.

## Network

The service joins only `media_net` for OPN-153. It binds to the configured media host LAN IP and port:

```yaml
ports:
  - "${GATEWAY_BIND_HOST}:${GATEWAY_PORT:-8088}:8080"
```

Restrict the host firewall so only the OpenClaw runtime IP can reach `GATEWAY_PORT`.

Example UFW shape:

```bash
sudo ufw allow from <openclaw-runtime-ip> to any port 8088 proto tcp
sudo ufw deny 8088/tcp
```

## Smoke Test

Run from a machine that can reach the gateway:

```bash
scripts/smoke-openclaw-gateway.sh http://192.168.1.103:8088 "$GATEWAY_AUTH_TOKEN"
```

The script checks `/health` without auth, then checks an authenticated Jellyfin search without printing the token.
```

- [ ] **Step 2: Add smoke test script**

Create `scripts/smoke-openclaw-gateway.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

gateway_url="${1:-${GATEWAY_URL:-}}"
gateway_token="${2:-${GATEWAY_AUTH_TOKEN:-}}"

if [[ -z "${gateway_url}" ]]; then
  echo "Usage: $0 <gateway-url> <gateway-token>" >&2
  echo "Or set GATEWAY_URL and GATEWAY_AUTH_TOKEN." >&2
  exit 2
fi

if [[ -z "${gateway_token}" ]]; then
  echo "Missing gateway token." >&2
  exit 2
fi

health_status="$(curl -fsS -o /dev/null -w "%{http_code}" "${gateway_url%/}/health")"
if [[ "${health_status}" != "200" ]]; then
  echo "Health check failed with HTTP ${health_status}." >&2
  exit 1
fi

search_status="$(
  curl -fsS \
    -o /dev/null \
    -w "%{http_code}" \
    -H "Authorization: Bearer ${gateway_token}" \
    "${gateway_url%/}/v1/media/jellyfin/search?q=smoke"
)"

if [[ "${search_status}" != "200" ]]; then
  echo "Authenticated Jellyfin search failed with HTTP ${search_status}." >&2
  exit 1
fi

echo "OpenClaw gateway smoke test passed."
```

- [ ] **Step 3: Make script executable**

Run:

```bash
chmod +x scripts/smoke-openclaw-gateway.sh
```

- [ ] **Step 4: Run shell syntax check**

Run:

```bash
bash -n scripts/smoke-openclaw-gateway.sh
```

Expected: no output and exit code `0`.

- [ ] **Step 5: Commit**

```bash
git add apps/openclaw-gateway/README.md scripts/smoke-openclaw-gateway.sh
git commit -m "OPN-153: document gateway operations"
```

### Task 8: Final Verification and Linear Update

**Files:**
- Modify only if verification finds a defect in files from earlier tasks.

- [ ] **Step 1: Run full Python tests**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 2: Validate Compose config**

Run:

```bash
docker compose --env-file apps/openclaw-gateway/example.env -f apps/openclaw-gateway/compose.yml config
```

Expected:

- service is named `openclaw-gateway`
- only Docker network is external `media_net`
- no `network_mode: host`
- no `/var/run/docker.sock` mount
- no media directory mounts
- port mapping uses `${GATEWAY_BIND_HOST}:${GATEWAY_PORT:-8088}:8080`

- [ ] **Step 3: Build the Docker image**

Run:

```bash
docker build -t openclaw-gateway:test apps/openclaw-gateway/openclaw-gateway
```

Expected: image builds successfully.

- [ ] **Step 4: Run smoke script syntax check**

Run:

```bash
bash -n scripts/smoke-openclaw-gateway.sh
```

Expected: no output and exit code `0`.

- [ ] **Step 5: Inspect changed files for secrets**

Run:

```bash
git diff --cached -- apps/openclaw-gateway scripts docs
git status --short
```

Expected: no real tokens, API keys, private keys, `.env` files, runtime histories, session logs, or sqlite state are staged or committed.

- [ ] **Step 6: Commit final fixes if any**

If Step 1-5 required edits, commit only those edits:

```bash
git add <fixed-files>
git commit -m "OPN-153: fix gateway verification issues"
```

- [ ] **Step 7: Add final Linear comment**

Add a Linear comment to `OPN-153`:

```markdown
Implementation complete.

What changed:
- Added `apps/openclaw-gateway` Dockerized FastAPI gateway.
- Added read-only Jellyfin and Jellyseerr normalized endpoints.
- Added bearer-token auth for `/v1/...` routes.
- Added gateway runbook and smoke test.

Verification:
- `python -m pytest -v` passed.
- `docker compose --env-file apps/openclaw-gateway/example.env -f apps/openclaw-gateway/compose.yml config` passed.
- `docker build -t openclaw-gateway:test apps/openclaw-gateway/openclaw-gateway` passed.
- `bash -n scripts/smoke-openclaw-gateway.sh` passed.

Follow-ups:
- OPN-156 tracks deferred Sonarr/Radarr read-only endpoints.
```

## Plan Self-Review

- Spec coverage: The plan covers the Dockerized FastAPI app, new `apps/openclaw-gateway` stack, `media_net` only, token auth, unauthenticated `/health`, read-only Jellyfin/Jellyseerr endpoints, normalized responses, fail-fast settings, no raw passthrough routes, no Docker socket, no host networking, no media mounts, docs, smoke test, and verification.
- Deferred scope: Sonarr/Radarr remain out of implementation and are tracked by OPN-156. Docker logs, Paperless, n8n, downloader/indexer access, Jellyseerr writes, and unified media search are not implemented.
- Placeholder scan: The only `change-me` values are intentional example env placeholders; real secrets are never included.
- Type consistency: `GatewaySettings`, `MediaItem`, `MediaSearchResponse`, `JellyfinClient`, `JellyseerrClient`, and `build_media_router` names are consistent across tasks.
