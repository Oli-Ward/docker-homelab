# OPN-156 Sonarr/Radarr Gateway Endpoints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit read-only Sonarr series and Radarr movie endpoints to the OpenClaw media gateway without exposing upstream API keys or raw passthrough routes.

**Architecture:** Follow the existing FastAPI gateway shape: settings hold upstream URLs/API keys, small httpx clients normalize upstream payloads into Pydantic schemas, and `routers/media.py` exposes fixed authenticated routes under `/v1/media`. Sonarr/Radarr data is manager-library/status data that Jellyfin/Jellyseerr do not reliably provide, such as monitored state, download/missing counts, path presence, and quality profile identifiers.

**Tech Stack:** Docker Compose, FastAPI, Pydantic settings, httpx, pytest, pytest-asyncio, respx.

---

### Task 1: Settings and Environment

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/settings.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_settings.py`
- Modify: `apps/openclaw-gateway/compose.yml`
- Modify: `apps/openclaw-gateway/example.env`

- [ ] **Step 1: Write the failing settings test**

Add `sonarr_url`, `sonarr_api_key`, `radarr_url`, and `radarr_api_key` to `valid_settings_kwargs()` and assert the normalized URL values in `test_settings_accept_valid_config`.

- [ ] **Step 2: Run the settings test to verify it fails**

Run: `cd apps/openclaw-gateway/openclaw-gateway && pytest tests/test_settings.py -q`
Expected: FAIL because `GatewaySettings` does not expose Sonarr/Radarr fields yet.

- [ ] **Step 3: Add minimal settings implementation**

Add required `AnyHttpUrl` and non-empty API key fields for Sonarr and Radarr to `GatewaySettings`.

- [ ] **Step 4: Add Compose/env references**

Add `SONARR_URL`, `SONARR_API_KEY`, `RADARR_URL`, and `RADARR_API_KEY` to `apps/openclaw-gateway/compose.yml` and safe placeholders to `apps/openclaw-gateway/example.env`.

- [ ] **Step 5: Run settings test again**

Run: `cd apps/openclaw-gateway/openclaw-gateway && pytest tests/test_settings.py -q`
Expected: PASS.

### Task 2: Normalized Arr Client Models

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/media.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/sonarr.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/radarr.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_sonarr_client.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_radarr_client.py`

- [ ] **Step 1: Write failing Sonarr client test**

Use `respx` to mock `GET http://sonarr:8989/api/v3/series` with `X-Api-Key` and assert a normalized response containing `id`, `title`, `year`, `monitored`, `status`, `path`, `quality_profile_id`, `statistics`, and `tags`.

- [ ] **Step 2: Run Sonarr test to verify it fails**

Run: `cd apps/openclaw-gateway/openclaw-gateway && pytest tests/test_sonarr_client.py -q`
Expected: FAIL because the client and schema do not exist yet.

- [ ] **Step 3: Implement minimal Sonarr client and schema**

Add `SeriesSummary`, `SeriesStatistics`, and `SeriesSummaryResponse` schemas, then implement `SonarrClient.series()` against `/api/v3/series`.

- [ ] **Step 4: Write failing Radarr client test**

Use `respx` to mock `GET http://radarr:7878/api/v3/movie` with `X-Api-Key` and assert normalized movie fields including availability, monitored state, downloaded state, path, quality profile ID, statistics, and tags.

- [ ] **Step 5: Run Radarr test to verify it fails**

Run: `cd apps/openclaw-gateway/openclaw-gateway && pytest tests/test_radarr_client.py -q`
Expected: FAIL because the Radarr client does not exist yet.

- [ ] **Step 6: Implement minimal Radarr client and schema**

Add `MovieSummary`, `MovieStatistics`, and `MovieSummaryResponse` schemas, then implement `RadarrClient.movies()` against `/api/v3/movie`.

- [ ] **Step 7: Run client tests**

Run: `cd apps/openclaw-gateway/openclaw-gateway && pytest tests/test_sonarr_client.py tests/test_radarr_client.py -q`
Expected: PASS.

### Task 3: Authenticated Read-Only Routes

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/media.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_media_routes.py`

- [ ] **Step 1: Write failing route tests**

Add tests for `GET /v1/media/sonarr/series` and `GET /v1/media/radarr/movies` that verify bearer auth is required and normalized JSON is returned when the client methods are monkeypatched.

- [ ] **Step 2: Run route tests to verify failure**

Run: `cd apps/openclaw-gateway/openclaw-gateway && pytest tests/test_media_routes.py -q`
Expected: FAIL because the routes and clients are not wired yet.

- [ ] **Step 3: Implement route wiring**

Import Sonarr/Radarr clients and response schemas, construct clients from settings, add fixed read-only GET routes, and reuse existing upstream error mapping.

- [ ] **Step 4: Run route tests**

Run: `cd apps/openclaw-gateway/openclaw-gateway && pytest tests/test_media_routes.py -q`
Expected: PASS.

### Task 4: Documentation and Smoke Coverage

**Files:**
- Modify: `apps/openclaw-gateway/README.md`
- Modify: `scripts/smoke-openclaw-gateway.sh`

- [ ] **Step 1: Update README endpoint and boundary docs**

Document the OpenClaw use case, endpoint shapes, required environment variables, and security boundary: no raw `/api/sonarr/*` or `/api/radarr/*`, read-only only, API keys stay on media host.

- [ ] **Step 2: Extend smoke script**

Add optional authenticated checks for `/v1/media/sonarr/series` and `/v1/media/radarr/movies` behind `CHECK_ARR_ENDPOINTS=1`, keeping default smoke behavior compatible with current deployments.

- [ ] **Step 3: Run full focused verification**

Run:
`cd apps/openclaw-gateway/openclaw-gateway && pytest -q`
`cd apps/openclaw-gateway && docker compose --env-file example.env config >/tmp/openclaw-gateway-compose.yml`
`bash -n scripts/smoke-openclaw-gateway.sh`

Expected: all commands pass, and no secret values are printed.

### Task 5: Linear Closeout

**Files:**
- No code files.

- [ ] **Step 1: Review diff**

Run: `git diff -- apps/openclaw-gateway scripts/smoke-openclaw-gateway.sh docs/superpowers/plans/2026-06-28-opn-156-sonarr-radarr-gateway-endpoints.md`

- [ ] **Step 2: Update OPN-156**

After verification passes, add a Linear final comment with outcome, changed files, verification commands/results, and follow-ups. Move the issue to `Done` only after verification passes.
