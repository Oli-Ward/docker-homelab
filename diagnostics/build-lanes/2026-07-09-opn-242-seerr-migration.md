# OPN-242 Seerr Migration Runbook

Date: 2026-07-09

## Scope

Migrate the media request-management app from Jellyseerr to Seerr using the official automatic migration path, without direct `docker compose up/down/pull` execution and without deleting the existing config path during the first pass.

## Official Constraints

- Seerr automatically migrates an existing Jellyseerr instance on first startup.
- Backup is required before cutover.
- The migration started on the official image `ghcr.io/seerr-team/seerr:latest`; the final repo uses `ghcr.io/seerr-team/seerr:preview-new-oidc` for Seerr native OIDC support.
- The container should have `init: true`.
- The container runs as UID `1000` and needs read/write access to `/app/config`.
- Docker service/container references must be renamed from `jellyseerr` to `seerr`.

## Local Repo Starting Point

- `apps/media/compose.yml` currently runs `fallenbagel/jellyseerr:preview-OIDC` as service/container `jellyseerr`.
- Config mount was `${APPDATA_ROOT}/jellyseerr:/app/config`.
- Homepage currently pointed to `https://jellyseerr.home.lab` and widget URL `http://jellyseerr:5055`.
- OpenClaw gateway currently defaulted `JELLYSEERR_URL` to `http://jellyseerr:5055`.
- Repo docs still described Jellyseerr by name.

## Migration Decisions

- Keep `${APPDATA_ROOT}/jellyseerr` for the first cutover and treat any host-path rename as a separate storage migration.
- Rename the running Docker service/container to `seerr`.
- First pass kept OpenClaw's `jellyseerr` route names and env variable names; final cleanup removed them in favor of `seerr`.
- Keep the historical external host in mind for this environment:
  - prior Jellyseerr traffic used `request.home.lab`
  - `jellyseerr.home.lab` was also previously used
- Promote `seerr.home.lab` as canonical, while retaining `request.home.lab` and/or `jellyseerr.home.lab` as temporary compatibility aliases during cutover.

## Approval Log

- Backup/checkpoint confirmed: Operator accepted proceeding after live Seerr validation; no fresh encrypted appdata artifact was found during preflight.
- Read-only live inventory approved: APPROVED (2026-07-09)
- Repo edits approved: APPROVED (2026-07-09)
- Media stack deployment approved: APPROVED (2026-07-09) [recheck confirms deployment complete]
- NPM/Auth/AdGuard cutover approved: COMPLETED during live migration
- Gateway/Homepage redeploy approved: pending redeploy of final repo cleanup (`SEERR_*`, `/v1/media/seerr/*`, Homepage `type: seerr`)

## Execution Log

- 2026-07-09: Repo-only edits complete for migration prep tasks.
  - Updated `apps/media/compose.yml` to `seerr` service/container using `ghcr.io/seerr-team/seerr:latest`, added `init: true`, `PORT=5055`, and preserved `${APPDATA_ROOT}/jellyseerr` mount.
  - Updated OpenClaw defaults and example env to `JELLYSEERR_URL=http://seerr:5055`.
  - Updated Homepage card to `Seerr` and canonical `https://seerr.home.lab` route with internal widget endpoint `http://seerr:5055`.
  - Updated README/CLAUDE/docs context for first-pass compatibility migration naming.
  - No live/container changes or Komodo/API actions have been run in this phase.
- 2026-07-09 Task 2: Read-only inventory and backup posture checks completed.
  - Repo reference scan (`rg` on all migration surfaces) returned only expected migration-related hits:
    - Compatibility names: `JELLYSEERR_*`, `jellyseerr` in mounted path names and legacy alias documentation.
    - Intentional backup note: `docs/backup/media-appdata.md` now documents `${APPDATA_ROOT}/jellyseerr` retention.
  - Live stack check (`docker ps`, `docker inspect jellyseerr`, `docker logs`) confirms only legacy runtime request app exists:
    - `jellyseerr` is running with image `fallenbagel/jellyseerr:preview-OIDC`.
    - Container name/service is still `jellyseerr` (no live `seerr` container yet).
    - Bind mount currently points to `/srv/appdata/jellyseerr:/app/config`.
  - Routing check (`curl` probes) confirmed:
    - `https://request.home.lab` now returns `HTTP 302` to `https://seerr.home.lab/`.
    - `https://jellyseerr.home.lab` now returns `HTTP 302` to `https://seerr.home.lab/`.
    - `https://seerr.home.lab` currently redirects unauthenticated traffic to Authentik `/outpost.goauthentik.io/start` (no TLS block observed).
  - Appdata ownership/mode check was re-routed via the live container (no host elevation needed):
    - `docker exec jellyseerr sh -lc "stat -c '%U:%G %u:%g %a %n' /app/config"` returns `node:node 1000:1000 775 /app/config`.
    - `docker exec jellyseerr` file listing shows `/app/config` is owned by `node:node` and writable by group, but existing items remain `root:root` (e.g., `cache`, `db`, `logs`, config JSONs).
    - This indicates mount-level ownership now matches Seerr UID expectations; pre-flight remediation should confirm whether root-owned content can be left in-place or requires a one-time `chown -R 1000:1000 /srv/appdata/jellyseerr` before Seerr startup.
- 2026-07-09 Task 2 Step 4 (backup confirmation): `media-appdata-<timestamp>.tar.gz.age` artifacts not found under `/mnt/backup/media-docker-appdata`; backup destination guard not present (`.opn-192-media-backups-ok` absent), so backup checkpoint not yet confirmed.
- 2026-07-09 Task 5 (pre-deploy prep): config ownership remediation completed on live bind mount.
  - `docker exec jellyseerr sh -lc "stat -c '%U:%G %u:%g %a %n' /app/config"` originally showed mount as `node:node 1000:1000 775`, but child entries were `root:root` on disk.
  - Executed in-container remediation: `chown -R 1000:1000 /app/config` (inside legacy `jellyseerr` container) to make appdata content writable by UID 1000 for Seerr startup.
  - Post-command verification:
    - `/app/config`, `/app/config/settings.json`, `/app/config/settings.old.json` are `node:node`.
    - `/app/config/cache`, `/app/config/db`, and `/app/config/logs` are `node:node` mode `755`.
- 2026-07-09 Task 5 Step 3 verification:
  - Recheck after user deployment confirm shows:
    - `seerr` is running with image `ghcr.io/seerr-team/seerr:latest`, up 2 minutes, and healthy.
    - `jellyseerr` is still running with image `fallenbagel/jellyseerr:preview-OIDC`, up 2 days.
    - `docker inspect seerr` reports compose service label `seerr` and container name `/seerr`.
    - Health check path is reachable from inside the container:
      - `docker exec seerr wget -qO- --timeout=10 http://127.0.0.1:5055/api/v1/settings/public`
    - Public settings endpoint currently reports `applicationUrl` as `https://request.home.lab` (legacy hostname carried from prior config).
  - External proxy checks:
    - `https://jellyseerr.home.lab` still resolves and redirects through Authentik (legacy hostname still active).
    - `https://request.home.lab` still follows the legacy request route, but HTTPS validation is currently blocked by TLS SNI in this environment.
    - `https://seerr.home.lab` still fails in this environment with TLS SNI (`tlsv1 unrecognized name`) and needs external TLS/router validation after deployment.
  - Logs show normal startup/migration behavior:
    - `Starting Seerr version 3.3.0`
    - `Server ready on port 5055`
  - Conclusion: Seerr container is present and healthy.
- 2026-07-09 Task 5 follow-up:
  - Confirmed legacy `jellyseerr` container is no longer running after cleanup.
  - `https://request.home.lab` and `https://jellyseerr.home.lab` are now HTTP 302 redirects to `https://seerr.home.lab/`.
  - `https://seerr.home.lab` is returning `HTTP/2 302` to `/outpost.goauthentik.io/start` (auth gate active, no TLS error now).
- 2026-07-09 Task 7 preflight compatibility check:
  - `apps/openclaw-gateway/.env` updated to `JELLYSEERR_URL=http://seerr:5055` to align runtime config with migrated service name.
  - Komodo redeploy was reported complete, but live container env still shows `JELLYSEERR_URL=http://jellyseerr:5055`, so the deployment likely re-used an external env override.
  - Gateway is reachable on host `192.168.1.103:8088` per compose mapping; local `127.0.0.1:8088` is not mapped in this environment.
  - API verification from this host to `http://192.168.1.103:8088/v1/media/jellyseerr/search?q=alien` timed out in this environment.
  - Live logs show healthy startup and current health/probe activity:
    - `Application startup complete.`
    - `Uvicorn running on http://0.0.0.0:8080`
  - Direct internal calls to `/v1/media/jellyseerr/search` from inside the gateway container did not complete successfully (auth/route validation remained inconclusive in this environment); `/health` and `.../v1/media/ryot/probe` behavior remains as expected for token-gated routes.
- 2026-07-10 final cleanup after operator confirmation:
  - Operator confirmed Seerr is working, Seerr integrations are working, and OpenClaw works against the migrated service.
  - OpenClaw compatibility names were removed from repo-managed gateway code and config:
    - `JELLYSEERR_URL` -> `SEERR_URL`
    - `JELLYSEERR_API_KEY` -> `SEERR_API_KEY`
    - `/v1/media/jellyseerr/search` -> `/v1/media/seerr/search`
    - `/v1/media/jellyseerr/requests` -> `/v1/media/seerr/requests`
    - `JellyseerrClient` -> `SeerrClient`
  - The legacy `/v1/media/jellyseerr/search` route is intentionally removed and now covered by a `404` regression test.
  - Homepage was updated to use the native Seerr widget:
    - `type: seerr`
    - `HOMEPAGE_VAR_SEERR_API_KEY`
  - The mounted appdata path remains `${APPDATA_ROOT}/jellyseerr` intentionally to avoid making the existing Seerr database/config disappear during a routine redeploy. Rename that path only in a separate storage-migration change with a backup and Komodo maintenance window.

## Validation

Task 4 executed:

- `docker compose config` pass:
  - `apps/media/compose.yml` rendered successfully and includes:
    - `services.seerr.container_name: seerr`
    - `services.seerr.image: ghcr.io/seerr-team/seerr:latest` at initial cutover; later repo cleanup uses `ghcr.io/seerr-team/seerr:preview-new-oidc`
    - `services.seerr.environment.PORT: "5055"`
    - `services.seerr.volumes` includes `/srv/appdata/jellyseerr:/app/config`
  - `apps/openclaw-gateway/compose.yml` rendered successfully with:
    - first pass rendered `JELLYSEERR_URL: http://seerr:5055`; final cleanup renders `SEERR_URL: http://seerr:5055`
  - `apps/utilities/compose.yml` render initially failed due shell glob expansion (`NODES_EXCLUDE=[]` in zsh), then passed after quoting and produced `/tmp/opn-242-utilities-compose.yml`.
- No syntax-level blocking issues were found before deployment.
- Final OpenClaw cleanup validation:
  - `pytest apps/openclaw-gateway/openclaw-gateway/tests/test_settings.py apps/openclaw-gateway/openclaw-gateway/tests/test_media_routes.py apps/openclaw-gateway/openclaw-gateway/tests/test_seerr_client.py apps/openclaw-gateway/openclaw-gateway/tests/test_smoke_script.py -q`
  - Result: `39 passed`.
  - `pytest apps/openclaw-gateway/openclaw-gateway/tests -q`
  - Result: `59 passed`.
  - Final non-deploying compose renders passed:
    - `apps/media/compose.yml` -> `/tmp/opn-242-media-compose.yml`
    - `apps/openclaw-gateway/compose.yml` -> `/tmp/opn-242-openclaw-compose.yml`
    - `apps/utilities/compose.yml` -> `/tmp/opn-242-utilities-compose.yml`
  - Rendered checks:
    - Media renders `services.seerr.image: ghcr.io/seerr-team/seerr:preview-new-oidc`.
    - OpenClaw renders `SEERR_URL: http://seerr:5055` and `SEERR_API_KEY`.
    - Utilities renders `HOMEPAGE_VAR_SEERR_API_KEY`.
  - Real gitignored env files were updated in place without printing secret values:
    - `apps/openclaw-gateway/.env`: `JELLYSEERR_URL`/`JELLYSEERR_API_KEY` renamed to `SEERR_URL`/`SEERR_API_KEY`.
    - `apps/utilities/.env`: `HOMEPAGE_VAR_JELLYSEERR_API_KEY` renamed to `HOMEPAGE_VAR_SEERR_API_KEY`.
  - Real-env compose renders passed:
    - `docker compose -f apps/openclaw-gateway/compose.yml --env-file apps/openclaw-gateway/.env config >/tmp/opn-242-openclaw-real-env-compose.yml`
    - `docker compose -f apps/utilities/compose.yml --env-file apps/utilities/.env config >/tmp/opn-242-utilities-real-env-compose.yml`
  - Real-env render checks confirmed OpenClaw has `SEERR_URL`/`SEERR_API_KEY`, utilities has `HOMEPAGE_VAR_SEERR_API_KEY`, and old Jellyseerr env keys are absent from the rendered configs.
  - After operator redeployed `openclaw-gateway` and `utilities` through Komodo, live verification passed:
    - `docker ps` shows `openclaw-gateway` up, `homepage` healthy, and `seerr` healthy on `ghcr.io/seerr-team/seerr:preview-new-oidc`.
    - Live `openclaw-gateway` container env contains `SEERR_URL` and `SEERR_API_KEY`; it does not contain `JELLYSEERR_URL` or `JELLYSEERR_API_KEY`.
    - Live `homepage` container env contains `HOMEPAGE_VAR_SEERR_API_KEY`; it does not contain `HOMEPAGE_VAR_JELLYSEERR_API_KEY`.
    - Gateway `/health` returned `200`.
    - Gateway `/v1/media/seerr/search?q=alien` returned `200`.
    - Legacy gateway `/v1/media/jellyseerr/search?q=alien` returned `404`.
    - `CHECK_SEERR_REQUESTS=1 ... scripts/smoke-openclaw-gateway.sh` passed.
    - Live Homepage config at `/app/config/services.yaml` contains `type: seerr` and `HOMEPAGE_VAR_SEERR_API_KEY`.

## Task 5 Deployment Completion / Verification

- `docker ps` showed only `seerr` after cutover:
  - `seerr` (`ghcr.io/seerr-team/seerr:latest` during initial cutover; repo later switched to `ghcr.io/seerr-team/seerr:preview-new-oidc` for native OIDC)
- Seerr process logs indicate healthy startup and readiness on port `5055`.
- Config ownership remediation on mounted `jellyseerr` appdata was applied before Seerr startup.
- Request-route remap is completed in NPM (`/data/nginx/proxy_host/4.conf`):
  - `server_name seerr.home.lab request.home.lab jellyseerr.home.lab`
  - `if ($host = request.home.lab) { return 302 https://seerr.home.lab$request_uri; }`
  - `if ($host = jellyseerr.home.lab) { return 302 https://seerr.home.lab$request_uri; }`
- Auth result:
  - Later Linear updates record Seerr native OIDC login working from the browser.
  - Final operator confirmation: Seerr is working, integrations are working, and OpenClaw works.

## Rollback

Rollback for the completed migration:

1. In Git, revert the OPN-242 Seerr migration commit(s) for media, OpenClaw gateway, Homepage, and docs.
2. Through Komodo, redeploy the media stack back to the previous Jellyseerr image/service only if Seerr itself must be rolled back.
3. Through Nginx Proxy Manager/Auth/DNS, restore `request.home.lab` and/or the prior request-app host as the primary route if needed.
4. Through Komodo, redeploy `openclaw-gateway` and `utilities` after reverting config.
5. If Seerr startup changed app data in a way that prevents rollback, restore `${APPDATA_ROOT}/jellyseerr` from the last known-good pre-cutover backup or VM checkpoint instead of attempting a reverse migration in-place.

Remaining follow-ups:

- Optional: rename `${APPDATA_ROOT}/jellyseerr` to `${APPDATA_ROOT}/seerr` in a separate storage migration after confirming a fresh backup/checkpoint.
- Optional: remove `request.home.lab` and `jellyseerr.home.lab` compatibility aliases after bookmarks and external references are gone.
