# OPN-248 Tdarr Media Health Transcode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Tdarr for careful media health-check/transcode evaluation using a tiny test library only.

**Architecture:** Tdarr belongs in `apps/media` because it is media-library processing infrastructure with a web UI. The initial service uses the Tdarr server with internal node enabled, mounts only a test library, stores state under `${APPDATA_ROOT}/tdarr`, and exposes UI through NPM/AuthentiK after deployment.

**Tech Stack:** Docker Compose, `ghcr.io/haveagitgat/tdarr:latest`, Tdarr internal node, Nginx Proxy Manager, AuthentiK, Homepage, Komodo.

## Global Constraints

- Komodo is the source of truth for deployment; do not run deploy/restart/pull commands directly without explicit permission.
- Do not enable full-library bulk transcoding by default.
- Do not remap existing media/download paths or make full media libraries writable in the first rollout.
- Start with a tiny copied test library mounted at `${DATA_ROOT}/tdarr-test-library`.
- Use a dedicated transcode cache at `${DATA_ROOT}/tdarr-transcode-cache`.
- Do not add GPU config unless `/dev/dri` or NVIDIA runtime support is explicitly confirmed.
- Protect `tdarr.home.lab` with AuthentiK through NPM before browser use.

---

## File Structure

- Modify `apps/media/compose.yml`: add `tdarr` service.
- Modify `apps/media/example.env`: document Tdarr test/cache paths and ports.
- Modify `apps/utilities/homepage/services.yaml`: add Tdarr dashboard entry.
- Modify `README.md`: add Tdarr and safe-rollout note.
- Create `docs/media/tdarr.md`: record initial scope, resource baseline, test-library policy, and keep/remove decision.

## Sources Checked

- Tdarr docs: https://docs.tdarr.io/
- Tdarr Docker Compose docs: https://docs.tdarr.io/docs/installation/docker/run-compose/
- Tdarr Docker image information: https://hub.docker.com/r/haveagitgat/tdarr

### Task 1: Add safe Tdarr service using test paths only

**Files:**
- Modify: `apps/media/compose.yml`
- Modify: `apps/media/example.env`

**Interfaces:**
- Consumes: existing `media_net`, `proxy_net`, `${APPDATA_ROOT}`, `${DATA_ROOT}`, `${TZ}`, `${PUID}`, `${PGID}`.
- Produces: `tdarr` server with internal node, web UI port `8265`, server port `8266`, test media mount, and transcode cache mount.

- [ ] **Step 1: Add env placeholders**

Append to `apps/media/example.env`:

```env

# Tdarr safe evaluation paths and ports
TDARR_TEST_LIBRARY_PATH=${DATA_ROOT}/tdarr-test-library
TDARR_TRANSCODE_CACHE_PATH=${DATA_ROOT}/tdarr-transcode-cache
TDARR_SERVER_PORT=8266
TDARR_WEBUI_PORT=8265
TDARR_INTERNAL_NODE=true
TDARR_NODE_NAME=media-internal-node
```

- [ ] **Step 2: Add Compose service**

Insert in `apps/media/compose.yml` before `networks:`:

```yaml
  # Tdarr - Media health checks and transcoding evaluation
  tdarr:
    image: ghcr.io/haveagitgat/tdarr:latest
    container_name: tdarr
    environment:
      - TZ=${TZ}
      - PUID=${PUID}
      - PGID=${PGID}
      - UMASK_SET=002
      - serverIP=0.0.0.0
      - serverPort=${TDARR_SERVER_PORT}
      - webUIPort=${TDARR_WEBUI_PORT}
      - internalNode=${TDARR_INTERNAL_NODE}
      - inContainer=true
      - ffmpegVersion=7
      - nodeName=${TDARR_NODE_NAME}
      - auth=false
      - openBrowser=false
      - maxLogSizeMB=10
    volumes:
      - ${APPDATA_ROOT}/tdarr/server:/app/server
      - ${APPDATA_ROOT}/tdarr/configs:/app/configs
      - ${APPDATA_ROOT}/tdarr/logs:/app/logs
      - ${TDARR_TEST_LIBRARY_PATH}:/media:rw
      - ${TDARR_TRANSCODE_CACHE_PATH}:/temp
    networks:
      - media_net
      - proxy_net
    restart: unless-stopped
```

- [ ] **Step 3: Do not add GPU devices in this task**

Do not add this block unless a separate hardware check confirms it is safe:

```yaml
    devices:
      - /dev/dri:/dev/dri
```

- [ ] **Step 4: Validate Compose without deploying**

Run from `apps/media` with safe placeholders:

```bash
PUID=1000 PGID=1000 TZ=Pacific/Auckland DATA_ROOT=/data APPDATA_ROOT=/srv/appdata RYOT_FRONTEND_URL=https://ryot.home.lab RYOT_POSTGRES_DB=ryot RYOT_POSTGRES_USER=ryot RYOT_POSTGRES_PASSWORD=change-me RYOT_SERVER_ADMIN_ACCESS_TOKEN=change-me RYOT_TMDB_ACCESS_TOKEN=change-me RYOT_DISABLE_TELEMETRY=true RYOT_USERS_ALLOW_REGISTRATION=true RYOT_OIDC_CLIENT_ID=change-me RYOT_OIDC_CLIENT_SECRET=change-me RYOT_OIDC_ISSUER_URL=https://auth.home.lab/application/o/ryot/ RYOT_OIDC_BUTTON_LABEL='Continue with Authentik' TDARR_TEST_LIBRARY_PATH=/data/tdarr-test-library TDARR_TRANSCODE_CACHE_PATH=/data/tdarr-transcode-cache TDARR_SERVER_PORT=8266 TDARR_WEBUI_PORT=8265 TDARR_INTERNAL_NODE=true TDARR_NODE_NAME=media-internal-node docker compose config
```

Expected: PASS, rendered config mounts `/data/tdarr-test-library` rather than full `/data/media`.

- [ ] **Step 5: Commit service config**

```bash
git add apps/media/compose.yml apps/media/example.env
git commit -m "OPN-248: add Tdarr safe test service"
```

### Task 2: Add dashboard and operational documentation

**Files:**
- Modify: `apps/utilities/homepage/services.yaml`
- Modify: `README.md`
- Create: `docs/media/tdarr.md`

**Interfaces:**
- Consumes: Tdarr service from Task 1.
- Produces: documented UI route and safe first-run procedure.

- [ ] **Step 1: Add Homepage entry**

Add under `Media & Downloads` in `apps/utilities/homepage/services.yaml`:

```yaml
    - Tdarr:
        icon: tdarr.png
        href: https://tdarr.home.lab
        description: Media health checks and transcoding
        siteMonitor: http://tdarr:8265
```

- [ ] **Step 2: Update README service catalog**

Add `Tdarr - Media health checks and transcoding evaluation` under Media in `README.md`.

- [ ] **Step 3: Add README safety note**

Add this bullet under `README.md` Notes:

```markdown
* Tdarr must start with the dedicated test library and no full-library bulk transcode until resource usage and output safety are proven.
```

- [ ] **Step 4: Create Tdarr documentation**

Create `docs/media/tdarr.md`:

```markdown
# Tdarr Evaluation

Tdarr is installed for health-check/transcode evaluation only. It must not process the full media library until a separate approval confirms CPU/RAM/disk headroom, backup posture, and output behavior.

## Initial Paths

- Test library: `${DATA_ROOT}/tdarr-test-library`
- Transcode cache: `${DATA_ROOT}/tdarr-transcode-cache`
- App state: `${APPDATA_ROOT}/tdarr`

## Initial Runtime Policy

- Add only copied sample files to the test library.
- Start with health checks before transcoding.
- Keep worker counts low in the UI.
- Do not replace originals until behavior is understood.
- Do not add GPU devices until hardware support is confirmed.

## External UI Checklist

- NPM host: `tdarr.home.lab` -> `tdarr:8265`.
- AuthentiK application/provider/outpost entry: `Tdarr`.
- AdGuard DNS record: `tdarr.home.lab` to NPM host.
- Homepage entry monitors `http://tdarr:8265`.

## First Test

1. Copy one small media file into `${DATA_ROOT}/tdarr-test-library`.
2. Confirm the UI sees only that test library.
3. Run one health check.
4. If transcoding is tested, process one copied file only.
5. Record CPU, RAM, disk, runtime, and Jellyfin playback result.

## Keep/Remove Decision

- Keep status: pending first test.
- Reason: pending resource and playback evidence.
```

- [ ] **Step 5: Commit docs/dashboard changes**

```bash
git add apps/utilities/homepage/services.yaml README.md docs/media/tdarr.md
git commit -m "OPN-248: document Tdarr safe rollout"
```

### Task 3: Manual deployment and validation checklist

**Files:**
- Modify: `docs/media/tdarr.md`

**Interfaces:**
- Consumes: deployed Tdarr service through Komodo.
- Produces: recorded evaluation result.

- [ ] **Step 1: Prepare host paths before deployment**

With user approval, create host directories:

```bash
mkdir -p "${DATA_ROOT}/tdarr-test-library" "${DATA_ROOT}/tdarr-transcode-cache" "${APPDATA_ROOT}/tdarr"
```

Expected: directories exist and are owned so container user `${PUID}:${PGID}` can write app state/cache.

- [ ] **Step 2: Deploy through Komodo**

Redeploy the media stack in Komodo. Do not run direct `docker compose up` unless explicitly approved.

- [ ] **Step 3: Configure external UI**

Configure outside the repo:

```text
NPM: tdarr.home.lab -> tdarr:8265
Authentik: application/provider/outpost entry for Tdarr
AdGuard: tdarr.home.lab DNS record/rewrite
```

- [ ] **Step 4: Run focused read-only diagnostics**

After deploy, with permission for read-only live inspection:

```bash
docker logs tdarr --tail=100
docker inspect tdarr
```

Expected: no startup loop, UI port is configured, and mounts point to test/cache paths.

- [ ] **Step 5: Record result**

Append to `docs/media/tdarr.md` after first test:

```markdown
## First Test Result

- Date: YYYY-MM-DD
- Test file count: record number
- Health check result: pass/fail
- Transcode tested: yes/no
- CPU/RAM/disk observation: record values
- Jellyfin playback result: pass/fail/not tested
- Keep status: keep/remove/defer
```

Replace `YYYY-MM-DD` and fields with exact observed values before committing.

- [ ] **Step 6: Commit evaluation result**

```bash
git add docs/media/tdarr.md
git commit -m "OPN-248: record Tdarr evaluation result"
```
