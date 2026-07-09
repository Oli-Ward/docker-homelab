# OPN-244 Backrest Restic Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Backrest as a protected restic Web UI/orchestrator for config and appdata backups, with a mandatory restore test before trust.

**Architecture:** Backrest belongs in `apps/utilities` because it is platform utility infrastructure with a web UI. It mounts selected config/appdata sources read-only, writes Backrest state under `${APPDATA_ROOT}/backrest`, and exposes UI only through NPM plus AuthentiK.

**Tech Stack:** Docker Compose, `ghcr.io/garethgeorge/backrest:latest`, restic, Nginx Proxy Manager, AuthentiK, Homepage, Komodo.

## Global Constraints

- Komodo is the source of truth for deployment; do not run deploy/restart/pull commands directly without explicit permission.
- Do not commit real restic repository passwords, rclone configs, `.env` files, API keys, private keys, backup artifacts, or restored secret material.
- First backup scope is important config/appdata only; do not enable bulk media or downloads backup in this ticket.
- A restore test to a temporary restore path is mandatory before treating the setup as usable.
- Protect `backrest.home.lab` with AuthentiK if exposed through NPM.
- Confirm backups/checkpoints exist before any restore test touches live paths; initial restore target must be temporary and outside live appdata.

---

## File Structure

- Modify `apps/utilities/compose.yml`: add `backrest` service.
- Modify `apps/utilities/example.env`: document `BACKREST_RESTIC_REPO_HOST_PATH` and `BACKREST_SOURCE_APPDATA_HOST_PATH` placeholders.
- Modify `apps/utilities/homepage/services.yaml`: add Backrest dashboard entry under System or a new Backups group.
- Modify `README.md`: add Backrest to Utilities and backup notes.
- Create `docs/backup/backrest.md`: record initial scope, excluded paths, retention/check/prune policy, and restore-test procedure.

## Sources Checked

- Backrest GitHub: https://github.com/garethgeorge/backrest
- Backrest docs: https://garethgeorge.github.io/backrest/
- Backrest Docker Hub: https://hub.docker.com/r/garethgeorge/backrest

### Task 1: Add Backrest service without backup jobs enabled

**Files:**
- Modify: `apps/utilities/compose.yml`
- Modify: `apps/utilities/example.env`

**Interfaces:**
- Consumes: existing `utilities_net`, `proxy_net`, `${APPDATA_ROOT}`, `${TZ}`.
- Produces: `backrest` container with persistent UI/config state and read-only selected source mounts.

- [ ] **Step 1: Add env placeholders**

Append to `apps/utilities/example.env`:

```env

# Backrest / restic backup management
BACKREST_RESTIC_REPO_HOST_PATH=/mnt/backup/restic
BACKREST_SOURCE_APPDATA_HOST_PATH=/srv/appdata
```

- [ ] **Step 2: Add the Compose service**

Insert this service in `apps/utilities/compose.yml` before `networks:`:

```yaml
  # Backrest - Restic backup management
  backrest:
    image: ghcr.io/garethgeorge/backrest:latest
    container_name: backrest
    hostname: backrest
    environment:
      - TZ=${TZ}
      - BACKREST_DATA=/data
      - BACKREST_CONFIG=/config/config.json
      - XDG_CACHE_HOME=/cache
      - TMPDIR=/tmp
    volumes:
      - ${APPDATA_ROOT}/backrest/data:/data
      - ${APPDATA_ROOT}/backrest/config:/config
      - ${APPDATA_ROOT}/backrest/cache:/cache
      - ${APPDATA_ROOT}/backrest/tmp:/tmp
      - ${APPDATA_ROOT}/backrest/rclone:/root/.config/rclone
      - ${BACKREST_SOURCE_APPDATA_HOST_PATH}:/userdata/appdata:ro
      - /home/oli/docker:/userdata/docker-repo:ro
      - ${BACKREST_RESTIC_REPO_HOST_PATH}:/repos
    networks:
      - utilities_net
      - proxy_net
    restart: unless-stopped
```

- [ ] **Step 3: Validate Compose without deploying**

Run from `apps/utilities` with safe placeholder paths:

```bash
PUID=1000 PGID=1000 TZ=Pacific/Auckland DATA_ROOT=/data APPDATA_ROOT=/srv/appdata HOMEPAGE_ALLOWED_HOSTS= HOMEPAGE_VAR_TITLE=Homelab HOMEPAGE_VAR_SPEEDTEST_API_KEY=change-me HOMEPAGE_VAR_JELLYFIN_API_KEY=change-me HOMEPAGE_VAR_QBITTORRENT_PASSWORD=change-me HOMEPAGE_VAR_NZBGET_PASSWORD=change-me HOMEPAGE_VAR_JELLYSEERR_API_KEY=change-me HOMEPAGE_VAR_PROWLARR_API_KEY=change-me HOMEPAGE_VAR_RADARR_API_KEY=change-me HOMEPAGE_VAR_SONARR_API_KEY=change-me HOMEPAGE_VAR_BAZARR_API_KEY=change-me HOMEPAGE_VAR_KOMODO_API_KEY=change-me HOMEPAGE_VAR_KOMODO_API_SECRET=change-me HOMEPAGE_VAR_TAILSCALE_API_KEY=change-me HOMEPAGE_VAR_ADGUARD_PASSWORD=change-me HOMEPAGE_VAR_AUTHENTIK_API_KEY=change-me HOMEPAGE_VAR_NPM_PASSWORD=change-me HOMEPAGE_VAR_CLEANUPARR_API_KEY=change-me HOMEPAGE_VAR_PAPERLESS_PASSWORD=change-me ICLOUD_USERNAME=example@example.com SPEEDTEST_KEY=base64:change-me SPEEDTEST_APP_URL=https://speedtest.home.lab NODES_EXCLUDE=[] LINEAR_OPENCLAW_WEBHOOK_SECRET=change-me BACKREST_RESTIC_REPO_HOST_PATH=/mnt/backup/restic BACKREST_SOURCE_APPDATA_HOST_PATH=/srv/appdata docker compose config
```

Expected: PASS, rendered config contains `backrest`, `/userdata/appdata:ro`, `/userdata/docker-repo:ro`, and `/repos`.

- [ ] **Step 4: Commit service config**

```bash
git add apps/utilities/compose.yml apps/utilities/example.env
git commit -m "OPN-244: add Backrest utility service"
```

### Task 2: Add dashboard and durable backup documentation

**Files:**
- Modify: `apps/utilities/homepage/services.yaml`
- Modify: `README.md`
- Create: `docs/backup/backrest.md`

**Interfaces:**
- Consumes: Backrest service from Task 1.
- Produces: operator-facing instructions for initial backup scope, AuthentiK/NPM setup, and restore verification.

- [ ] **Step 1: Add Homepage entry**

Add this under `System` in `apps/utilities/homepage/services.yaml`:

```yaml
    - Backrest:
        icon: mdi-backup-restore
        href: https://backrest.home.lab
        description: Restic backup management
        siteMonitor: http://backrest:9898
```

- [ ] **Step 2: Update README service catalog**

Add `Backrest - Restic backup management` under Utilities in `README.md`.

- [ ] **Step 3: Create backup documentation**

Create `docs/backup/backrest.md`:

```markdown
# Backrest Restic Backup Management

Backrest manages restic repositories and schedules for selected homelab configuration and appdata. It complements full VM backups and the existing manual encrypted media appdata workflow; it does not replace either until restore tests are proven.

## Initial Scope

Include first:

- `/userdata/docker-repo` for this Docker Compose repository, read-only.
- `/userdata/appdata/jellyfin`
- `/userdata/appdata/jellyseerr`
- `/userdata/appdata/sonarr`
- `/userdata/appdata/radarr`
- `/userdata/appdata/prowlarr`
- `/userdata/appdata/bazarr`
- `/userdata/appdata/cleanuparr`
- `/userdata/appdata/maintainerr`
- `/userdata/appdata/nginx-proxy-manager/data`
- `/userdata/appdata/nginx-proxy-manager/letsencrypt`

Exclude initially:

- Bulk media libraries.
- Downloads and incomplete downloads.
- Transcode caches.
- Paperless exports and state.
- Authentik PostgreSQL until a dedicated maintenance plan exists.
- Komodo MongoDB until a dedicated maintenance plan exists.

## Repository

- Initial repository path inside the container: `/repos/media-config`.
- Store the restic password only in Backrest/runtime secret storage, not in this repository.
- Keep repository storage mounted at `${BACKREST_RESTIC_REPO_HOST_PATH}` on the host.

## Retention

Initial retention policy:

- Keep 7 daily snapshots.
- Keep 4 weekly snapshots.
- Keep 6 monthly snapshots.
- Run repository check weekly.
- Run prune after forget, outside heavy media/download windows.

## NPM and AuthentiK

Create NPM proxy host:

- Hostname: `backrest.home.lab`
- Forward hostname: `backrest`
- Forward port: `9898`
- Scheme: `http`
- SSL: existing internal `home.lab` policy
- Auth: existing AuthentiK proxy-auth pattern

Keep Backrest's own login enabled if feasible.

## Restore Test

Do not restore over live appdata as the first test.

1. Confirm the backup repository has at least one completed snapshot.
2. Create a temporary restore target inside Backrest, such as `/tmp/backrest-restore-check`.
3. Restore one small non-secret file from `/userdata/docker-repo/README.md` to the temporary target.
4. Confirm the restored file exists and has sane permissions.
5. Record snapshot ID, source path, restore target, and result in the Linear final update.
```

- [ ] **Step 4: Manual UI work checklist**

After Komodo deploy, configure outside the repo:

```text
NPM: backrest.home.lab -> backrest:9898
Authentik: application/provider/outpost entry for Backrest
Backrest UI: create /repos/media-config repository
Backrest UI: create initial config/appdata plan with retention/check/prune policy
Backrest UI: run one small backup and one temporary restore test
```

- [ ] **Step 5: Commit documentation/dashboard changes**

```bash
git add apps/utilities/homepage/services.yaml README.md docs/backup/backrest.md
git commit -m "OPN-244: document Backrest backup rollout"
```
