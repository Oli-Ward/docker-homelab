# OPN-270 Plane SDK Extraction — Design Spec

**Goal:** Extract `openclaw_plane_sdk` from the gateway project into an independently installable Python package at `packages/openclaw-plane-sdk/`, consumed by the gateway and future services (Plane MCP tool, CLI helpers) as a local path dependency.

---

## Context

`openclaw_plane_sdk` currently lives as a sibling directory inside `apps/openclaw-gateway/openclaw-gateway/` and is co-declared in the gateway's `pyproject.toml`. This means any downstream consumer of the SDK must install the entire gateway package — pulling in FastAPI, uvicorn, and pydantic-settings — even though those are gateway-only concerns. The SDK's only runtime requirements are httpx and pydantic.

The immediate consumers of the standalone SDK are:

- `openclaw-gateway` (OPN-264) — already imports from `openclaw_plane_sdk`
- Plane MCP tool for ChatGPT/Codex (OPN-272) — needs `PlaneClient` without gateway deps

---

## Layout After OPN-270

```text
repo/
├── .dockerignore                         ← new; scoped to SDK + gateway build inputs
├── packages/
│   └── openclaw-plane-sdk/
│       ├── pyproject.toml                ← new; httpx + pydantic only
│       ├── src/
│       │   └── openclaw_plane_sdk/
│       │       ├── __init__.py           ← moved verbatim from gateway
│       │       ├── client.py             ← moved verbatim from gateway
│       │       └── models.py             ← moved verbatim from gateway
│       └── tests/
│           └── test_plane_client.py      ← moved verbatim from gateway tests
│
└── apps/
    └── openclaw-gateway/
        ├── compose.yml                   ← build block widened to repo root
        └── openclaw-gateway/
            ├── Dockerfile                ← COPY paths updated for repo-root context
            ├── pyproject.toml            ← SDK as path dep; openclaw_plane_sdk* removed
            ├── openclaw_gateway/         ← unchanged
            └── tests/
                └── (test_plane_client.py removed; all others unchanged)
```

---

## Components

### `packages/openclaw-plane-sdk/pyproject.toml`

```toml
[project]
name = "openclaw-plane-sdk"
version = "0.1.0"
description = "Reusable Plane API client for OpenClaw services"
requires-python = ">=3.12"
dependencies = [
  "httpx>=0.28",
  "pydantic>=2",
]

[project.optional-dependencies]
test = [
  "pytest>=8",
  "pytest-asyncio>=0.25",
  "respx>=0.22",
]

[tool.setuptools.packages.find]
where = ["src"]
include = ["openclaw_plane_sdk*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

No FastAPI, uvicorn, pydantic-settings, or gateway configuration. The SDK only needs an HTTP client and model validation.

### Gateway `pyproject.toml` changes

```toml
[project]
dependencies = [
  "openclaw-plane-sdk",
  "fastapi==0.115.6",
  "httpx==0.28.1",
  "pydantic-settings==2.7.1",
  "uvicorn[standard]==0.34.0",
]

[tool.uv.sources]
openclaw-plane-sdk = { path = "../../../packages/openclaw-plane-sdk", editable = true }

[tool.setuptools.packages.find]
include = ["openclaw_gateway*"]
```

The relative path `../../../packages/openclaw-plane-sdk` is correct from `apps/openclaw-gateway/openclaw-gateway/pyproject.toml` to the repo root and then into `packages/`.

`[tool.uv.sources]` is only read by `uv`. `pip` ignores it, so fresh-environment installs via pip must install the SDK explicitly before the gateway (see verification below). The Docker build handles this by installing `/build/openclaw-plane-sdk` before the gateway.

### Dockerfile

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY packages/openclaw-plane-sdk /build/openclaw-plane-sdk
RUN pip install --no-cache-dir /build/openclaw-plane-sdk

COPY apps/openclaw-gateway/openclaw-gateway/pyproject.toml /app/pyproject.toml
COPY apps/openclaw-gateway/openclaw-gateway/openclaw_gateway /app/openclaw_gateway

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["uvicorn", "openclaw_gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

`/build/` signals build-time input. The gateway's `pyproject.toml` does not currently declare `readme` or `license` file references, so no additional COPY is needed before `pip install .`.

### `apps/openclaw-gateway/compose.yml` build block

```yaml
build:
  context: ../..
  dockerfile: apps/openclaw-gateway/openclaw-gateway/Dockerfile
```

`../..` resolves relative to `apps/openclaw-gateway/compose.yml`, giving the repository root. All paths in the Dockerfile are then relative to that root.

### Repo-root `.dockerignore`

Required because widening the build context to the repo root would otherwise send the entire repository — including `.git/`, venvs, caches, and secrets — to the Docker daemon.

Must exclude:

```text
.git/
**/.venv/
**/__pycache__/
**/.pytest_cache/
**/.mypy_cache/
**/.ruff_cache/
**/*.pyc
.env
.env.*
ssl/
```

Must not exclude:

```text
packages/openclaw-plane-sdk/
apps/openclaw-gateway/openclaw-gateway/
```

The `.dockerignore` uses the same glob syntax as `.gitignore`. Exclusions apply from the build context root.

---

## What Changes, What Does Not

| Location | Change |
|---|---|
| `packages/openclaw-plane-sdk/` | New directory; SDK files moved here |
| `apps/openclaw-gateway/openclaw-gateway/openclaw_plane_sdk/` | Deleted |
| `apps/openclaw-gateway/openclaw-gateway/tests/test_plane_client.py` | Moved to SDK |
| `apps/openclaw-gateway/openclaw-gateway/pyproject.toml` | SDK as path dep; packages.find updated |
| `apps/openclaw-gateway/openclaw-gateway/Dockerfile` | COPY paths updated |
| `apps/openclaw-gateway/compose.yml` | Build context widened |
| `.dockerignore` | Added at repo root |
| `openclaw_gateway/clients/plane.py` | Unchanged — thin re-export stays |
| `openclaw_gateway/schemas/workflow.py` | Unchanged — already imports from SDK |
| `openclaw_gateway/routers/workflow.py` | Unchanged — already imports from SDK |
| All other gateway tests | Unchanged |

The gateway's Python imports are already correct — `clients/plane.py`, `schemas/workflow.py`, and `routers/workflow.py` all import from `openclaw_plane_sdk`, not from a gateway-local copy. No Python source files in `openclaw_gateway/` require modification.

---

## Dependency Graph After Extraction

```
openclaw-plane-sdk   [httpx, pydantic]
        ↑
   ┌────┴────────────────┐
gateway              MCP service (OPN-272)
[fastapi, uvicorn,   [mcp, ...]
 pydantic-settings]
```

Neither the gateway nor the MCP service pulls the other's dependencies through the SDK.

---

## Verification Gates

### 1. SDK tests run independently

```bash
cd packages/openclaw-plane-sdk
uv run --extra test pytest -q
```

Expected: all tests pass with no gateway package on the path.

### 2. SDK wheel builds and installs cleanly

```bash
cd packages/openclaw-plane-sdk
pip install build
python -m build
python -m venv /tmp/openclaw-plane-sdk-test
source /tmp/openclaw-plane-sdk-test/bin/activate
pip install dist/openclaw_plane_sdk-*.whl
python -c "from openclaw_plane_sdk import PlaneClient; print(PlaneClient)"
deactivate
```

Catches incorrect `src` layout discovery, missing package-data, and metadata errors that editable installs can hide.

### 3. No gateway imports leak into the SDK

```bash
rg "openclaw_gateway|fastapi|uvicorn|pydantic_settings" \
  packages/openclaw-plane-sdk/src packages/openclaw-plane-sdk/pyproject.toml
```

Expected: no matches.

### 4. Gateway suite passes with SDK as path dependency

```bash
cd apps/openclaw-gateway/openclaw-gateway
uv sync
uv run pytest -q
```

Or with explicit pip, for environments without uv:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e "../../../packages/openclaw-plane-sdk[test]"
pip install -e ".[test]"
pytest -q
```

### 5. Container builds from the widened context

```bash
docker compose -f apps/openclaw-gateway/compose.yml build --no-cache
```

Expected: exits 0; image contains both `openclaw_plane_sdk` and `openclaw_gateway`.

### 6. Runtime dependency isolation

```bash
docker compose -f apps/openclaw-gateway/compose.yml \
  run --rm openclaw-gateway pip show openclaw-plane-sdk
```

Expected: shows `Requires: httpx, pydantic` only. FastAPI, uvicorn, and pydantic-settings are present in the image because the gateway needs them, but they must not appear in the SDK's `Requires` field.

---

## Out of Scope

- Flattening `apps/openclaw-gateway/openclaw-gateway/` to `apps/openclaw-gateway/` — separate ticket
- Publishing `openclaw-plane-sdk` to PyPI or a private registry
- MCP tool implementation (OPN-272) — SDK extraction is the prerequisite
- CLI helper — comes after gateway and MCP consumers exist
