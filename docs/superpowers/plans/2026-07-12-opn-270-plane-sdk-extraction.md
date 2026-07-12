# OPN-270 Plane SDK Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract `openclaw_plane_sdk` from the gateway project into a standalone installable Python package at `packages/openclaw-plane-sdk/`, consumed by the gateway as a local uv path dependency.

**Architecture:** The SDK gets its own `pyproject.toml` with only `httpx` and `pydantic` as runtime deps. Source files and tests move via `git mv`. The gateway points at the new package via `[tool.uv.sources]`. The Docker build context widens to the repo root so the Dockerfile can COPY both the SDK and gateway source. A root-level `.dockerignore` scopes the build context to prevent sending the entire repository to Docker.

**Tech Stack:** Python 3.12+, httpx, pydantic, pytest, respx, pytest-asyncio, setuptools (src layout), uv (path deps), Docker.

---

### Task 1: SDK Package Scaffold and Tests

**Files:**
- Create: `packages/openclaw-plane-sdk/pyproject.toml`
- Move: `apps/openclaw-gateway/openclaw-gateway/openclaw_plane_sdk/__init__.py` → `packages/openclaw-plane-sdk/src/openclaw_plane_sdk/__init__.py`
- Move: `apps/openclaw-gateway/openclaw-gateway/openclaw_plane_sdk/client.py` → `packages/openclaw-plane-sdk/src/openclaw_plane_sdk/client.py`
- Move: `apps/openclaw-gateway/openclaw-gateway/openclaw_plane_sdk/models.py` → `packages/openclaw-plane-sdk/src/openclaw_plane_sdk/models.py`
- Move: `apps/openclaw-gateway/openclaw-gateway/tests/test_plane_client.py` → `packages/openclaw-plane-sdk/tests/test_plane_client.py`

- [ ] **Step 1: Create SDK directory structure**

```bash
mkdir -p packages/openclaw-plane-sdk/src/openclaw_plane_sdk
mkdir -p packages/openclaw-plane-sdk/tests
```

- [ ] **Step 2: Write `packages/openclaw-plane-sdk/pyproject.toml`**

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

- [ ] **Step 3: Move SDK source files with `git mv`**

```bash
git mv apps/openclaw-gateway/openclaw-gateway/openclaw_plane_sdk/__init__.py \
       packages/openclaw-plane-sdk/src/openclaw_plane_sdk/__init__.py

git mv apps/openclaw-gateway/openclaw-gateway/openclaw_plane_sdk/client.py \
       packages/openclaw-plane-sdk/src/openclaw_plane_sdk/client.py

git mv apps/openclaw-gateway/openclaw-gateway/openclaw_plane_sdk/models.py \
       packages/openclaw-plane-sdk/src/openclaw_plane_sdk/models.py
```

The source files are moved; the directory still exists because of `__pycache__/`. Remove it:

```bash
rm -rf apps/openclaw-gateway/openclaw-gateway/openclaw_plane_sdk
```

- [ ] **Step 4: Move the SDK test file with `git mv`**

```bash
git mv apps/openclaw-gateway/openclaw-gateway/tests/test_plane_client.py \
       packages/openclaw-plane-sdk/tests/test_plane_client.py
```

- [ ] **Step 5: Verify the module is not importable before installation**

Confirms the move landed correctly and the src layout requires explicit install:

```bash
cd packages/openclaw-plane-sdk
python -c "from openclaw_plane_sdk import PlaneClient" 2>&1
```

Expected: `ModuleNotFoundError: No module named 'openclaw_plane_sdk'`

- [ ] **Step 6: Install SDK and run its tests**

```bash
cd packages/openclaw-plane-sdk
uv run --extra test pytest -q
```

Expected: 9 tests pass, 0 failures. No import from `openclaw_gateway`.

If `uv` is not available:

```bash
cd packages/openclaw-plane-sdk
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
pytest -q
deactivate
```

- [ ] **Step 7: Verify no gateway imports leak into the SDK**

```bash
rg "openclaw_gateway|fastapi|uvicorn|pydantic_settings" \
  packages/openclaw-plane-sdk/src packages/openclaw-plane-sdk/pyproject.toml
```

Expected: no output (exit 0, zero matches).

- [ ] **Step 8: Verify the SDK wheel builds and installs as an artifact**

Catches src-layout discovery errors that editable installs can hide:

```bash
cd packages/openclaw-plane-sdk
pip install build
python -m build

python -m venv /tmp/openclaw-plane-sdk-gate
source /tmp/openclaw-plane-sdk-gate/bin/activate
pip install dist/openclaw_plane_sdk-*.whl
python -c "from openclaw_plane_sdk import PlaneClient; print(PlaneClient)"
deactivate
rm -rf /tmp/openclaw-plane-sdk-gate
```

Expected: `<class 'openclaw_plane_sdk.client.PlaneClient'>` printed, exit 0.

- [ ] **Step 9: Commit**

```bash
git add packages/openclaw-plane-sdk/
git commit -m "OPN-270: extract Plane SDK into standalone package"
```

---

### Task 2: Gateway Path Dependency

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/pyproject.toml`

After Task 1, the gateway's `openclaw_plane_sdk/` directory is gone and `tests/test_plane_client.py` has moved. The gateway `pyproject.toml` still lists `openclaw_plane_sdk*` in `packages.find` and has no SDK dependency — this task fixes that.

- [ ] **Step 1: Confirm the gateway tests are currently broken**

```bash
cd apps/openclaw-gateway/openclaw-gateway
uv run pytest -q 2>&1 | tail -5
```

Expected: errors or failures because `openclaw_plane_sdk` is no longer in the gateway directory and is not yet declared as a package dependency. This is the expected red state before the fix.

- [ ] **Step 2: Replace `apps/openclaw-gateway/openclaw-gateway/pyproject.toml`**

```toml
[project]
name = "openclaw-gateway"
version = "0.1.0"
description = "Internal OpenClaw capability gateway for selected homelab APIs"
requires-python = ">=3.12"
dependencies = [
  "openclaw-plane-sdk",
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

[tool.uv.sources]
openclaw-plane-sdk = { path = "../../../packages/openclaw-plane-sdk", editable = true }

[tool.setuptools.packages.find]
include = ["openclaw_gateway*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Key changes from the original:
- Added `"openclaw-plane-sdk"` to `dependencies`
- Added `[tool.uv.sources]` with the relative path from this `pyproject.toml` to `packages/openclaw-plane-sdk/`
- Changed `packages.find` `include` from `["openclaw_gateway*", "openclaw_plane_sdk*"]` to `["openclaw_gateway*"]`

- [ ] **Step 3: Sync and run the gateway test suite**

```bash
cd apps/openclaw-gateway/openclaw-gateway
uv sync
uv run pytest -q
```

Expected: all tests pass. `test_plane_client.py` is no longer in this test run — those tests now live in the SDK package.

If `uv` is not available:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m venv .venv && source .venv/bin/activate
pip install -e "../../../packages/openclaw-plane-sdk[test]"
pip install -e ".[test]"
pytest -q
deactivate
```

- [ ] **Step 4: Commit**

```bash
git add apps/openclaw-gateway/openclaw-gateway/pyproject.toml
git commit -m "OPN-270: point gateway at openclaw-plane-sdk path dependency"
```

---

### Task 3: Docker Build Context and .dockerignore

**Files:**
- Modify: `apps/openclaw-gateway/compose.yml`
- Modify: `apps/openclaw-gateway/openclaw-gateway/Dockerfile`
- Create: `.dockerignore`

- [ ] **Step 1: Update the build block in `apps/openclaw-gateway/compose.yml`**

Replace:

```yaml
    build: ./openclaw-gateway
```

With:

```yaml
    build:
      context: ../..
      dockerfile: apps/openclaw-gateway/openclaw-gateway/Dockerfile
```

`../..` resolves relative to `apps/openclaw-gateway/compose.yml` and gives the repository root. All Dockerfile `COPY` paths are then relative to that root.

- [ ] **Step 2: Replace `apps/openclaw-gateway/openclaw-gateway/Dockerfile`**

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

Changes from the original:
- Removed `COPY openclaw_plane_sdk /app/openclaw_plane_sdk` (SDK is no longer in the gateway directory)
- Added `COPY packages/openclaw-plane-sdk /build/openclaw-plane-sdk` and its `pip install` before the gateway install
- Changed `COPY pyproject.toml` and `COPY openclaw_gateway` to use full paths from the repo root

- [ ] **Step 3: Create `.dockerignore` at the repository root**

```text
# Git history
.git/

# Python build artifacts
**/__pycache__/
**/*.pyc
**/*.pyo
**/.pytest_cache/
**/.mypy_cache/
**/.ruff_cache/
**/.venv/
**/dist/
**/*.egg-info/

# Local secrets
.env
.env.*
**/.env
**/.env.*

# TLS certificates (contain private keys)
ssl/

# Stacks not needed for the gateway image
apps/arr-stack/
apps/downloads/
apps/media/
apps/utilities/
identity/
infra/
platform/
docs/
```

`packages/openclaw-plane-sdk/` and `apps/openclaw-gateway/openclaw-gateway/` are not excluded.

- [ ] **Step 4: Verify the compose config is valid**

```bash
docker compose -f apps/openclaw-gateway/compose.yml \
  --env-file apps/openclaw-gateway/example.env config --quiet
```

Expected: exits 0 with no errors or warnings.

- [ ] **Step 5: Build the image from the widened context**

```bash
docker compose -f apps/openclaw-gateway/compose.yml build --no-cache
```

Expected: exits 0. Both the SDK install step and the gateway install step complete without errors.

- [ ] **Step 6: Verify SDK runtime dependency isolation inside the image**

```bash
docker compose -f apps/openclaw-gateway/compose.yml \
  run --rm openclaw-gateway pip show openclaw-plane-sdk
```

Expected output contains:

```
Name: openclaw-plane-sdk
Version: 0.1.0
Requires: httpx, pydantic
```

`Requires` must not list `fastapi`, `uvicorn`, or `pydantic-settings`. Those packages are present in the image because the gateway needs them, but they must not appear as SDK dependencies.

- [ ] **Step 7: Commit**

```bash
git add apps/openclaw-gateway/compose.yml \
        apps/openclaw-gateway/openclaw-gateway/Dockerfile \
        .dockerignore
git commit -m "OPN-270: widen Docker build context for SDK extraction"
```

---

### Task 4: Verification and Linear

**Files:**
- Modify: this plan file as checkboxes complete.

- [ ] **Step 1: Run the full verification suite**

```bash
# Gate 1 — SDK tests run independently
cd packages/openclaw-plane-sdk
uv run --extra test pytest -q

# Gate 2 — SDK wheel builds and installs as an artifact
pip install build
python -m build
python -m venv /tmp/sdk-gate-2
source /tmp/sdk-gate-2/bin/activate
pip install dist/openclaw_plane_sdk-*.whl
python -c "from openclaw_plane_sdk import PlaneClient; print('wheel ok:', PlaneClient)"
deactivate
rm -rf /tmp/sdk-gate-2

# Gate 3 — No gateway imports in SDK source or metadata
cd /home/oli/docker  # run from repo root
rg "openclaw_gateway|fastapi|uvicorn|pydantic_settings" \
  packages/openclaw-plane-sdk/src packages/openclaw-plane-sdk/pyproject.toml

# Gate 4 — Gateway suite passes with SDK as path dep
cd apps/openclaw-gateway/openclaw-gateway
uv sync && uv run pytest -q

# Gate 5 — Container builds from widened context (already verified in Task 3 Step 5)
docker compose -f apps/openclaw-gateway/compose.yml build --no-cache

# Gate 6 — Runtime dep isolation (already verified in Task 3 Step 6)
docker compose -f apps/openclaw-gateway/compose.yml \
  run --rm openclaw-gateway pip show openclaw-plane-sdk
```

Expected: all gates pass. Gate 3 produces no output.

- [ ] **Step 2: Update Linear**

Update OPN-270 in Linear with:
- Commit hashes from Tasks 1–3
- Confirmation that all six verification gates passed
- Note that `packages/openclaw-plane-sdk` is ready for OPN-272 (Plane MCP tool) to consume with a `[tool.uv.sources]` path dependency
