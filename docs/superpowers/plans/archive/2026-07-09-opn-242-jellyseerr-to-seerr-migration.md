# OPN-242 Jellyseerr To Seerr Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current Jellyseerr deployment with official Seerr while preserving requests/config data, keeping OpenClaw and Homepage working, and minimizing auth and routing breakage during the cutover.

**Architecture:** Use Seerr's official automatic migration path instead of inventing a manual database migration. The first pass should rename the running app and route to Seerr, but deliberately keep the existing appdata path and the current OpenClaw `jellyseerr` API contract so the blast radius stays bounded. Deploy through Komodo only, then update Nginx Proxy Manager, Authentik, AdGuard, and Homepage in a staged sequence with rollback points between stacks.

**Tech Stack:** Docker Compose, Komodo, Seerr official Docker image, Nginx Proxy Manager, Authentik, AdGuard, Homepage, OpenClaw gateway, Markdown.

---

## Planned File Changes

- `apps/media/compose.yml`
  Replace the `jellyseerr` service with `seerr`, switch to the official `ghcr.io/seerr-team/seerr` image, add `init: true`, keep the homelab CA mount, and keep the existing `${APPDATA_ROOT}/jellyseerr:/app/config` bind mount for the first migration.
- `apps/openclaw-gateway/compose.yml`
  Keep the existing `JELLYSEERR_*` env var names for compatibility, but change the default upstream host from `jellyseerr` to `seerr`.
- `apps/openclaw-gateway/example.env`
  Update the example upstream URL to `http://seerr:5055` without renaming the variables yet.
- `apps/utilities/homepage/services.yaml`
  Rename the user-facing Homepage card to `Seerr`, point the href at `https://seerr.home.lab`, and point the widget URL at `http://seerr:5055`. Keep the existing `jellyseerr` widget type and API key variable unless Homepage support for a dedicated `seerr` widget is separately verified.
- `README.md`
  Rename the user-facing service references from Jellyseerr to Seerr and update the documented hostname to `seerr.home.lab`. If a compatibility alias will remain, document that separately.
- `CLAUDE.md`
  Update the architecture notes that currently describe Jellyseerr and the preview OIDC image so they match the official Seerr image and the new naming.
- `docs/backup/media-appdata.md`
  Keep the existing backup scope but add a note that the first Seerr migration intentionally keeps the appdata path under `jellyseerr` for rollback safety.
- `diagnostics/build-lanes/2026-07-09-opn-242-seerr-migration.md`
  Record approvals, read-only findings, migration decisions, execution notes, verification results, and rollback evidence.

## Key Migration Decisions

- Use the official Seerr Docker image: `ghcr.io/seerr-team/seerr:latest`.
- Do not perform manual database migration. Per the official Seerr migration guide, the first Seerr startup automatically migrates an existing Jellyseerr instance.
- Do not rename `${APPDATA_ROOT}/jellyseerr` during the first migration. Changing both the runtime and the storage path in one step adds unnecessary rollback risk.
- Rename the Docker service and container to `seerr` in the repo so internal service discovery matches the new product name.
- Keep OpenClaw's public API shape and env var names on the first pass:
  - `/v1/media/jellyseerr/search`
  - `/v1/media/jellyseerr/requests`
  - `JELLYSEERR_URL`
  - `JELLYSEERR_API_KEY`
- Promote `seerr.home.lab` as the canonical external hostname, but retain `request.home.lab` and/or `jellyseerr.home.lab` as temporary redirect or protected aliases until bookmarks and dependent docs are updated.
- Confirm `${APPDATA_ROOT}/jellyseerr` is writable by UID `1000` before starting Seerr, because the official container runs as the `node` user.

## Approval Boundary

This ticket spans repo changes, three Komodo-managed stacks, and external UI configuration. Execution should stay in this order:

1. Report-only planning and repo prep.
2. Read-only live inventory and backup confirmation.
3. Repo edits plus non-deploying compose validation.
4. Media stack deployment through Komodo.
5. NPM, Authentik, and AdGuard route cutover.
6. OpenClaw gateway redeploy through Komodo.
7. Homepage redeploy through Komodo.
8. Post-cutover verification.

Do not collapse these phases into one step.

### Task 1: Record Baseline, Constraints, And Operator Approval

**Files:**
- Create: `diagnostics/build-lanes/2026-07-09-opn-242-seerr-migration.md`
- Create: `docs/superpowers/plans/2026-07-09-opn-242-jellyseerr-to-seerr-migration.md`

- [ ] **Step 1: Create the migration runbook**

Create `diagnostics/build-lanes/2026-07-09-opn-242-seerr-migration.md` with:

```markdown
# OPN-242 Seerr Migration Runbook

Date: 2026-07-09

## Scope

Migrate the homelab request-management app from Jellyseerr to Seerr using the official automatic migration path, without direct `docker compose up/down/pull` usage and without deleting the existing config path during the first pass.

## Official Constraints

- Seerr automatically migrates an existing Jellyseerr instance on first startup.
- Backup is required before cutover.
- The official image is `ghcr.io/seerr-team/seerr:latest`.
- The container now requires `init: true`.
- The container runs as UID `1000` and needs read/write access to `/app/config`.
- Docker references should be renamed from `jellyseerr` to `seerr`.

## Local Repo Starting Point

- `apps/media/compose.yml` currently runs `fallenbagel/jellyseerr:preview-OIDC` as service/container `jellyseerr`.
- The current config mount is `${APPDATA_ROOT}/jellyseerr:/app/config`.
- Homepage currently points to `https://jellyseerr.home.lab` and widget URL `http://jellyseerr:5055`.
- OpenClaw gateway currently defaults `JELLYSEERR_URL` to `http://jellyseerr:5055`.
- Repo docs still describe Jellyseerr by name.

## Migration Decisions

- Keep `${APPDATA_ROOT}/jellyseerr` for the first cutover.
- Rename the running Docker service/container to `seerr`.
- Keep OpenClaw's `jellyseerr` route names and env variable names in the first pass.
- Promote `seerr.home.lab` as canonical and keep `request.home.lab` and/or `jellyseerr.home.lab` only as temporary compatibility aliases.

## Approval Log

- Backup/checkpoint confirmed: PENDING
- Read-only live inventory approved: PENDING
- Repo edits approved: PENDING
- Media stack deployment approved: PENDING
- NPM/Auth/AdGuard cutover approved: PENDING
- Gateway/Homepage redeploy approved: PENDING

## Execution Log

Pending.

## Verification

Pending.

## Rollback

Pending.
```

- [ ] **Step 2: Record explicit operator approvals before any live work**

Ask for approvals in this order and copy the user response into the runbook:

```text
1. Read-only live inventory and backup confirmation.
2. Repo edits for media, gateway, Homepage, and docs.
3. Komodo redeploy of the media stack.
4. NPM, Authentik, and AdGuard route cutover.
5. Komodo redeploy of openclaw-gateway and utilities.
```

Expected: each stage is clearly approved before proceeding to the next one.

### Task 2: Run Read-Only Inventory And Confirm Backup Posture

**Files:**
- Modify: `diagnostics/build-lanes/2026-07-09-opn-242-seerr-migration.md`

- [ ] **Step 1: Verify repo references that must move**

Run:

```bash
rg -n "jellyseerr|JELLYSEERR|jellyseerr.home.lab|fallenbagel/jellyseerr|preview-OIDC" \
  apps/media/compose.yml \
  apps/openclaw-gateway/compose.yml \
  apps/openclaw-gateway/example.env \
  apps/utilities/homepage/services.yaml \
  docs/backup/media-appdata.md \
  README.md \
  CLAUDE.md
```

Expected: matches appear only in the known migration surfaces above.

- [ ] **Step 2: Confirm the current config path owner and mode**

Run:

```bash
sudo stat -c '%U:%G %u:%g %a %n' "${APPDATA_ROOT}/jellyseerr"
sudo find "${APPDATA_ROOT}/jellyseerr" -maxdepth 1 -printf '%u:%g %m %p\n' | head -20
```

Expected: ownership and permissions are visible enough to decide whether a `chown -R 1000:1000` step is needed before Seerr starts.

- [ ] **Step 3: Capture current live routing and container evidence**

Run:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' | rg 'jellyseerr|openclaw-gateway|homepage|nginx-proxy-manager|authentik'
docker inspect jellyseerr
docker logs --tail 120 jellyseerr
curl -k -sS -I --max-time 10 https://jellyseerr.home.lab | sed -n '1,16p'
curl -k -sS -I --max-time 10 https://seerr.home.lab | sed -n '1,16p' || true
```

Expected:

- `jellyseerr` exists and is the current live request app.
- `seerr.home.lab` is either absent or not yet the active route.
- Logs and inspect output reveal enough to compare live drift against the repo without printing secrets.

- [ ] **Step 4: Confirm backups or checkpoints exist before migration**

Record one of the following in the runbook:

```text
- A confirmed VM snapshot/checkpoint timestamp that predates the cutover.
- A confirmed encrypted appdata backup artifact that includes the jellyseerr subtree.
- An explicit operator statement that they accept proceeding without a fresh rollback artifact.
```

Expected: the runbook contains a concrete rollback reference, not a vague note.

### Task 3: Apply Repo Changes For The Migration

**Files:**
- Modify: `apps/media/compose.yml`
- Modify: `apps/openclaw-gateway/compose.yml`
- Modify: `apps/openclaw-gateway/example.env`
- Modify: `apps/utilities/homepage/services.yaml`
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `docs/backup/media-appdata.md`

- [ ] **Step 1: Replace the media service with official Seerr**

Update `apps/media/compose.yml` so the request service becomes:

```yaml
  # Seerr - Request Management
  seerr:
    image: ghcr.io/seerr-team/seerr:latest
    init: true
    container_name: seerr
    networks:
      - media_net
      - proxy_net
    environment:
      - LOG_LEVEL=info
      - TZ=${TZ}
      - PORT=5055
      - NODE_EXTRA_CA_CERTS=/usr/local/share/ca-certificates/home-lab-root.crt
    volumes:
      - ${APPDATA_ROOT}/jellyseerr:/app/config
      - /home/oli/docker/ssl/home-lab-root.crt:/usr/local/share/ca-certificates/home-lab-root.crt:ro
    healthcheck:
      test: wget --no-verbose --tries=1 --spider http://localhost:5055/api/v1/settings/public || exit 1
      start_period: 20s
      timeout: 3s
      interval: 15s
      retries: 3
    restart: unless-stopped
```

Do not rename the host path to `${APPDATA_ROOT}/seerr` in this task.

- [ ] **Step 2: Point OpenClaw at the renamed internal host**

Update `apps/openclaw-gateway/compose.yml` and `apps/openclaw-gateway/example.env` so they still use the existing variable names but now default to:

```env
JELLYSEERR_URL=http://seerr:5055
```

Expected: the gateway contract stays stable while Docker service discovery follows the renamed container.

- [ ] **Step 3: Update Homepage to the new canonical route**

Update the Homepage card to:

```yaml
    - Seerr:
        icon: jellyseerr.png
        href: https://seerr.home.lab
        description: Request Media
        widget:
          type: jellyseerr
          url: http://seerr:5055
          key: "{{HOMEPAGE_VAR_JELLYSEERR_API_KEY}}"
```

Do not rename `HOMEPAGE_VAR_JELLYSEERR_API_KEY` in this pass.

- [ ] **Step 4: Update documentation to reflect the compatibility-first migration**

Apply these documentation rules:

- `README.md`: rename user-facing service references to `Seerr`, update the documented hostname to `seerr.home.lab`, and note that the first migration keeps the old appdata path for safety.
- `CLAUDE.md`: remove references to `preview-OIDC` for Jellyseerr and replace them with the official Seerr image plus the current auth/routing description.
- `docs/backup/media-appdata.md`: keep the backup example path as `jellyseerr`, but label it as the Seerr config path retained for migration compatibility.

Expected: the docs no longer imply that `fallenbagel/jellyseerr:preview-OIDC` is the intended steady state.

### Task 4: Validate Repo Rendering Before Any Deploy

**Files:**
- Check: `apps/media/compose.yml`
- Check: `apps/openclaw-gateway/compose.yml`
- Check: `apps/utilities/homepage/services.yaml`

- [ ] **Step 1: Render the media stack**

Run:

```bash
env PUID=1000 PGID=1000 TZ=Pacific/Auckland DATA_ROOT=/data APPDATA_ROOT=/srv/appdata \
  RYOT_FRONTEND_URL=https://ryot.home.lab \
  RYOT_POSTGRES_USER=change-me \
  RYOT_POSTGRES_PASSWORD=change-me \
  RYOT_POSTGRES_DB=change-me \
  RYOT_SERVER_ADMIN_ACCESS_TOKEN=change-me \
  RYOT_TMDB_ACCESS_TOKEN=change-me \
  RYOT_DISABLE_TELEMETRY=true \
  RYOT_USERS_ALLOW_REGISTRATION=false \
  RYOT_OIDC_CLIENT_ID=change-me \
  RYOT_OIDC_CLIENT_SECRET=change-me \
  RYOT_OIDC_ISSUER_URL=https://auth.home.lab/application/o/example/ \
  RYOT_OIDC_BUTTON_LABEL=Authentik \
  docker compose -f apps/media/compose.yml config >/tmp/opn-242-media-compose.yml
```

Expected: `docker compose config` exits `0` and the rendered service name is `seerr`.

- [ ] **Step 2: Render the gateway stack**

Run:

```bash
env GATEWAY_BIND_HOST=192.0.2.10 \
  GATEWAY_PORT=8088 \
  GATEWAY_AUTH_TOKEN=change-me \
  JELLYFIN_URL=http://jellyfin:8096 \
  JELLYFIN_API_KEY=change-me \
  JELLYSEERR_URL=http://seerr:5055 \
  JELLYSEERR_API_KEY=change-me \
  SONARR_URL=http://sonarr:8989 \
  SONARR_API_KEY=change-me \
  RADARR_URL=http://radarr:7878 \
  RADARR_API_KEY=change-me \
  RYOT_URL=http://ryot:8000 \
  RYOT_ADMIN_ACCESS_TOKEN=change-me \
  N8N_WEBHOOK_BASE_URL=http://n8n:5678 \
  N8N_OPENCLAW_SMOKE_PATH=/webhook/openclaw-smoke \
  N8N_JELLYFIN_RATING_PROMPT_PATH=/webhook/jellyfin-rating-prompt \
  docker compose -f apps/openclaw-gateway/compose.yml config >/tmp/opn-242-openclaw-compose.yml
```

Expected: `docker compose config` exits `0` and the rendered `JELLYSEERR_URL` points at `http://seerr:5055`.

- [ ] **Step 3: Render the utilities stack if Homepage config changed**

Run:

```bash
env PUID=1000 PGID=1000 TZ=Pacific/Auckland DATA_ROOT=/data APPDATA_ROOT=/srv/appdata \
  HOMEPAGE_ALLOWED_HOSTS=dash.home.lab \
  HOMEPAGE_VAR_TITLE=Homelab \
  HOMEPAGE_VAR_SPEEDTEST_API_KEY=change-me \
  HOMEPAGE_VAR_JELLYFIN_API_KEY=change-me \
  HOMEPAGE_VAR_QBITTORRENT_PASSWORD=change-me \
  HOMEPAGE_VAR_NZBGET_PASSWORD=change-me \
  HOMEPAGE_VAR_JELLYSEERR_API_KEY=change-me \
  HOMEPAGE_VAR_PROWLARR_API_KEY=change-me \
  HOMEPAGE_VAR_RADARR_API_KEY=change-me \
  HOMEPAGE_VAR_SONARR_API_KEY=change-me \
  HOMEPAGE_VAR_BAZARR_API_KEY=change-me \
  HOMEPAGE_VAR_KOMODO_API_KEY=change-me \
  HOMEPAGE_VAR_KOMODO_API_SECRET=change-me \
  HOMEPAGE_VAR_TAILSCALE_API_KEY=change-me \
  HOMEPAGE_VAR_ADGUARD_PASSWORD=change-me \
  HOMEPAGE_VAR_AUTHENTIK_API_KEY=change-me \
  HOMEPAGE_VAR_NPM_PASSWORD=change-me \
  HOMEPAGE_VAR_CLEANUPARR_API_KEY=change-me \
  HOMEPAGE_VAR_PAPERLESS_PASSWORD=change-me \
  ICLOUD_USERNAME=example@icloud.com \
  SPEEDTEST_KEY=example-speedtest-key \
  SPEEDTEST_APP_URL=https://speedtest.home.lab \
  N8N_PORT=5678 \
  N8N_SECURE_COOKIE=false \
  NODES_EXCLUDE=[] \
  OPENCLAW_SSH_HOST=192.0.2.16 \
  OPENCLAW_SSH_USER=openclaw \
  OPENCLAW_SSH_PORT=22 \
  OPENCLAW_SSH_KEY_PATH_HOST=/home/oli/.ssh/openclaw/openclaw_lab_tunnel \
  OPENCLAW_SSH_KEY_PATH=/home/node/.n8n/ssh/openclaw_lab_tunnel \
  OPENCLAW_WORKSPACE=/home/openclaw/.openclaw/workspace \
  OPENCLAW_RATING_PROMPT_DB=tracking/jellyfin-rating-prompts/rating-prompts.sqlite \
  docker compose -f apps/utilities/compose.yml --env-file apps/utilities/example.env config >/tmp/opn-242-utilities-compose.yml
```

Expected: `docker compose config` exits `0`.

### Task 5: Cut Over The Live Media Stack Through Komodo

**Files:**
- External UI: Komodo
- Modify: `diagnostics/build-lanes/2026-07-09-opn-242-seerr-migration.md`

- [ ] **Step 1: Fix appdata ownership if needed before deploy**

If Task 2 showed ownership is not writable by UID `1000`, run:

```bash
sudo chown -R 1000:1000 "${APPDATA_ROOT}/jellyseerr"
sudo find "${APPDATA_ROOT}/jellyseerr" -maxdepth 1 -printf '%u:%g %m %p\n' | head -20
```

Expected: the config tree is owned by `1000:1000` before Seerr starts.

- [ ] **Step 2: Deploy only the media stack through Komodo**

In Komodo, redeploy the stack that points at `apps/media/compose.yml`.

Expected:

- the old `jellyseerr` container is replaced by `seerr`
- the new image is `ghcr.io/seerr-team/seerr:latest`
- `jellyfin`, `ryot`, and `ryot-db` remain unaffected except for normal stack recreation order

- [ ] **Step 3: Verify automatic migration completed**

Run:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | rg 'seerr|jellyseerr'
docker logs --tail 200 seerr
curl -sS --max-time 10 http://127.0.0.1:5055/api/v1/settings/public || true
```

Expected:

- `seerr` is running
- no `jellyseerr` container remains in the live stack
- the logs show normal startup and do not show fatal permission errors for `/app/config`

### Task 6: Cut Over Routing, Auth, And DNS

**Files:**
- External UI/API: Nginx Proxy Manager
- External UI/API: Authentik
- External UI/API: AdGuard
- Modify: `diagnostics/build-lanes/2026-07-09-opn-242-seerr-migration.md`

- [ ] **Step 1: Update the NPM upstream to the renamed Docker service**

Change the protected request-app proxy host so the upstream becomes:

```text
Scheme: http
Forward Hostname / IP: seerr
Forward Port: 5055
```

If creating the new canonical host now, use:

```text
Primary host: seerr.home.lab
Legacy alias: request.home.lab and/or jellyseerr.home.lab
```

Expected: NPM no longer proxies to `jellyseerr:5055`.

- [ ] **Step 2: Update Authentik to match the canonical hostname**

In Authentik, update the application/provider/outpost configuration so the primary external host is:

```text
https://seerr.home.lab
```

If `request.home.lab` or `jellyseerr.home.lab` must remain temporarily, keep it/them only as compatibility aliases and not as the long-term primary host.

Expected: the protected route still redirects unauthenticated users through Authentik after the host rename.

- [ ] **Step 3: Update AdGuard so the new hostname resolves**

Create or update the DNS entry for:

```text
seerr.home.lab
```

If keeping a legacy alias, keep:

```text
request.home.lab, and optionally jellyseerr.home.lab -> same target as seerr.home.lab
```

Expected: both names resolve during the transition, but `seerr.home.lab` is the canonical one.

### Task 7: Redeploy Dependent Stacks And Verify Compatibility

**Files:**
- External UI: Komodo
- Check: `apps/openclaw-gateway/compose.yml`
- Check: `apps/utilities/homepage/services.yaml`

- [ ] **Step 1: Redeploy openclaw-gateway through Komodo**

Redeploy the stack that points at `apps/openclaw-gateway/compose.yml`.

Then verify:

```bash
docker logs --tail 120 openclaw-gateway
curl -sS -H "Authorization: Bearer ${GATEWAY_AUTH_TOKEN}" \
  "http://127.0.0.1:8080/v1/media/jellyseerr/search?q=alien"
```

- Confirm container runtime `JELLYSEERR_URL` in logs/environment matches `http://seerr:5055` before claiming Step 1 complete.

If `openclaw-gateway` base image lacks `curl`, run the request from another host/container that can reach port 8080 or via the external mapped port in `GATEWAY_BIND_HOST:GATEWAY_PORT`.

Expected:

- the gateway starts cleanly
- the existing `/v1/media/jellyseerr/search` route still works
- no gateway code changes were needed for the first pass

- [ ] **Step 2: Redeploy utilities through Komodo if Homepage changed**

Redeploy the stack that points at `apps/utilities/compose.yml`.

Then verify the Homepage card:

```text
- label shows Seerr
- clicking the card opens https://seerr.home.lab
- the widget still loads data from the Seerr API
```

Expected: Homepage works without renaming the widget secret variable.

- [ ] **Step 3: Verify the canonical and legacy URLs**

Run:

```bash
curl -k -sS -I --max-time 10 https://seerr.home.lab | sed -n '1,16p'
curl -k -sS -I --max-time 10 https://request.home.lab | sed -n '1,16p'
curl -k -sS -I --max-time 10 https://jellyseerr.home.lab | sed -n '1,16p' || true
```

Expected:

- `seerr.home.lab` is the working protected route
- `request.home.lab` and/or `jellyseerr.home.lab` either redirect to `seerr.home.lab` or remain protected as temporary aliases
- neither host exposes an unauthenticated direct login path

### Task 8: Finish Documentation And Rollback Notes

**Files:**
- Modify: `diagnostics/build-lanes/2026-07-09-opn-242-seerr-migration.md`
- Check: `README.md`
- Check: `CLAUDE.md`
- Check: `docs/backup/media-appdata.md`

- [ ] **Step 1: Capture final drift and compatibility notes**

Add these notes to the runbook if still true after cutover:

```markdown
- The live app is now Seerr, but the config path intentionally remains `${APPDATA_ROOT}/jellyseerr`.
- OpenClaw still exposes `jellyseerr` route names for compatibility.
- Homepage still uses the `jellyseerr` widget type and `HOMEPAGE_VAR_JELLYSEERR_API_KEY` for compatibility.
- `request.home.lab` and/or `jellyseerr.home.lab` remain only as temporary aliases, if they exist at all.
```

- [ ] **Step 2: Document rollback**

Record this rollback sequence in the runbook:

```text
1. Restore the pre-cutover repo state for media, gateway, Homepage, and docs.
2. Redeploy the media stack through Komodo back to the Jellyseerr image/service.
3. Point NPM/Auth/AdGuard back to request.home.lab and/or jellyseerr.home.lab and upstream seerr:5055 if needed.
4. Redeploy openclaw-gateway and utilities through Komodo.
5. If Seerr's first startup changed app data in a way that breaks rollback, restore `${APPDATA_ROOT}/jellyseerr` from the confirmed pre-cutover backup rather than relying on reverse migration.
```

Expected: rollback instructions are concrete and reference the actual retained config path.

- [ ] **Step 3: Record post-cutover follow-ups**

Create a follow-up list in the runbook for any intentionally deferred cleanup:

```text
- Optional: rename `${APPDATA_ROOT}/jellyseerr` to `${APPDATA_ROOT}/seerr` in a separate ticket after a successful steady-state period.
- Optional: rename OpenClaw `JELLYSEERR_*` env vars and `/v1/media/jellyseerr/*` routes in a compatibility-breaking cleanup ticket.
- Optional: replace `request.home.lab` and/or `jellyseerr.home.lab` aliases entirely after bookmarks and docs have been updated.
- Optional: switch Homepage icon/secret naming only after support for a dedicated Seerr widget and naming policy is verified.
```

---

## Self-Review

- **Spec coverage:** This plan covers the official Seerr automatic migration path, backup posture, config-permission requirement, Compose image/init changes, Komodo deployment, NPM/Auth/AdGuard cutover, OpenClaw compatibility, Homepage compatibility, docs, and rollback.
- **Placeholder scan:** No `TODO`, `TBD`, or undefined follow-through steps are left in the execution tasks.
- **Type consistency:** The first-pass compatibility names are consistent across the plan:
  - Docker service/container: `seerr`
  - Config path: `${APPDATA_ROOT}/jellyseerr`
  - Gateway env vars and routes: `JELLYSEERR_*`, `/v1/media/jellyseerr/*`
  - Canonical external hostname: `seerr.home.lab`
