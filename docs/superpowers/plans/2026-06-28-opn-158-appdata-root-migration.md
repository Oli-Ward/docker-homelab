# OPN-158 Appdata Root Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move mutable container app state mounts from `/data/configs` to a dedicated `${APPDATA_ROOT}` while keeping media, downloads, photos, and repo-managed Homepage config under their current roots.

**Architecture:** Compose files remain simple per-stack manifests. `${DATA_ROOT}` continues to mean user data such as media, downloads, photos, and broad read-only Homepage browsing; `${APPDATA_ROOT}` becomes the root for mutable app state such as `/config`, databases, generated service state, cookies, queues, and cert/config state. This is repo/config-only work: no live data movement, no container restarts, no pulls, and no Komodo deployment from this session.

**Tech Stack:** Docker Compose YAML, example env files, Markdown docs, non-deploying `docker compose config` validation.

---

## File Structure

- Modify `apps/utilities/compose.yml`: keep `./homepage:/app/config`, `${DATA_ROOT}:/data:ro`, and `${DATA_ROOT}/media/Photos:/data`; move Glances, iCloudPD config, Speedtest Tracker, and n8n state to `${APPDATA_ROOT}`. Also remove the malformed empty Homepage environment list item that currently blocks YAML/Compose validation.
- Modify `apps/utilities/example.env`: add `APPDATA_ROOT=/srv/appdata`.
- Modify `apps/arr-stack/compose.yml`: move Radarr, Sonarr, Prowlarr, Bazarr, Autoscan, and Cleanuparr `/config` mounts to `${APPDATA_ROOT}`; keep media and downloads on `${DATA_ROOT}`.
- Modify `apps/media/compose.yml`: move Jellyfin and Jellyseerr app state to `${APPDATA_ROOT}`; keep media mounts on `${DATA_ROOT}`.
- Modify `apps/media/example.env`: add `APPDATA_ROOT=/srv/appdata`.
- Modify `apps/downloads/compose.yml`: move qBittorrent, NZBGet, FlareSolverr, and Gluetun app state to `${APPDATA_ROOT}`; keep downloads on `${DATA_ROOT}`.
- Modify `apps/docs/compose.yml`: move Paperless PostgreSQL, Redis, application data, document media, consume, and export directories to `${APPDATA_ROOT}/paperless/...` because the current ticket defines these as mutable app-managed state, not general media library storage.
- Modify `apps/docs/example.env`: add `APPDATA_ROOT=/srv/appdata`.
- Modify `apps/docs/README.md`: update Paperless paths, migration warning, and directory creation examples to `${APPDATA_ROOT}`.
- Modify `infra/proxy/nginx-proxy-manager/compose.yml`: replace hard-coded `/data/configs/nginx-proxy-manager/...` with `${APPDATA_ROOT}/nginx-proxy-manager/...`.
- Modify `infra/dns/adguard/compose.yml`: replace hard-coded `/data/configs/adguard/...` with `${APPDATA_ROOT}/adguard/...`.
- Modify `infra/dns/adguard/.env.example`: add `APPDATA_ROOT=/srv/appdata`.
- Modify `AGENTS.md`: update repo conventions so app state uses `${APPDATA_ROOT}` and `/data` is reserved for media/downloads/photos/user data.
- Modify `CLAUDE.md`: update the same data-root convention to avoid stale local guidance.
- Modify `README.md`: add the `/data` versus `${APPDATA_ROOT}` split and preserve the existing RAM diagnostics section.
- Create `docs/migrations/2026-06-28-opn-158-appdata-root-migration.md`: stack-by-stack operator checklist with backups, copy/sync command shape, ownership checks, compose validation, Komodo redeploy, and rollback.

## Task 1: Compose Mount Migration

**Files:**
- Modify: `apps/utilities/compose.yml`
- Modify: `apps/arr-stack/compose.yml`
- Modify: `apps/media/compose.yml`
- Modify: `apps/downloads/compose.yml`
- Modify: `apps/docs/compose.yml`
- Modify: `infra/proxy/nginx-proxy-manager/compose.yml`
- Modify: `infra/dns/adguard/compose.yml`

- [ ] **Step 1: Replace mutable app-state mounts**

Apply these exact path rules:

```text
${DATA_ROOT}/configs/glances -> ${APPDATA_ROOT}/glances
${DATA_ROOT}/configs/icloudpd -> ${APPDATA_ROOT}/icloudpd
${DATA_ROOT}/configs/speedtest-tracker -> ${APPDATA_ROOT}/speedtest-tracker
${DATA_ROOT}/configs/n8n -> ${APPDATA_ROOT}/n8n
${DATA_ROOT}/configs/radarr -> ${APPDATA_ROOT}/radarr
${DATA_ROOT}/configs/sonarr -> ${APPDATA_ROOT}/sonarr
${DATA_ROOT}/configs/prowlarr -> ${APPDATA_ROOT}/prowlarr
${DATA_ROOT}/configs/bazarr -> ${APPDATA_ROOT}/bazarr
${DATA_ROOT}/configs/autoscan -> ${APPDATA_ROOT}/autoscan
${DATA_ROOT}/configs/cleanuparr -> ${APPDATA_ROOT}/cleanuparr
${DATA_ROOT}/configs/jellyfin -> ${APPDATA_ROOT}/jellyfin
${DATA_ROOT}/configs/jellyseerr -> ${APPDATA_ROOT}/jellyseerr
${DATA_ROOT}/configs/qbittorrent -> ${APPDATA_ROOT}/qbittorrent
${DATA_ROOT}/configs/nzbget -> ${APPDATA_ROOT}/nzbget
${DATA_ROOT}/configs/flaresolverr -> ${APPDATA_ROOT}/flaresolverr
${DATA_ROOT}/configs/gluetun -> ${APPDATA_ROOT}/gluetun
${DATA_ROOT}/configs/paperless -> ${APPDATA_ROOT}/paperless
/data/configs/nginx-proxy-manager -> ${APPDATA_ROOT}/nginx-proxy-manager
/data/configs/adguard -> ${APPDATA_ROOT}/adguard
```

Keep these mounts on `${DATA_ROOT}`:

```text
${DATA_ROOT}:/data:ro
${DATA_ROOT}/media/Photos:/data
${DATA_ROOT}/media/movies:/movies
${DATA_ROOT}/media/tv:/tv
${DATA_ROOT}/media/movies:/data/movies
${DATA_ROOT}/media/tv:/data/tv
${DATA_ROOT}/downloads:/downloads
```

Keep this Homepage exception as repo-managed config:

```text
./homepage:/app/config
```

- [ ] **Step 2: Repair malformed Utilities YAML**

In `apps/utilities/compose.yml`, delete the empty list item after `HOMEPAGE_VAR_PAPERLESS_PASSWORD`:

```yaml
      - 
```

Do not remove the Homepage secret environment variables that were already present in the dirty worktree.

- [ ] **Step 3: Verify no stale mutable mounts remain**

Run:

```bash
rg -n '\$\{DATA_ROOT\}/configs|/data/configs' apps infra identity platform AGENTS.md CLAUDE.md README.md docs --glob '!docs/superpowers/plans/**'
```

Expected: only historical design/spec/plan references remain, or documented migration notes that intentionally describe old paths.

## Task 2: Example Environment Files

**Files:**
- Modify: `apps/utilities/example.env`
- Modify: `apps/media/example.env`
- Modify: `apps/docs/example.env`
- Modify: `infra/dns/adguard/.env.example`

- [ ] **Step 1: Add APPDATA_ROOT placeholders**

Add this safe placeholder next to `DATA_ROOT` in each example env file that belongs to a stack using `${APPDATA_ROOT}`:

```env
APPDATA_ROOT=/srv/appdata
```

- [ ] **Step 2: Check env coverage**

Run:

```bash
rg -l '\$\{APPDATA_ROOT\}' apps infra identity platform | while read -r compose; do dir=$(dirname "$compose"); ls "$dir"/example.env "$dir"/.env.example "$dir"/compose.example.env >/dev/null 2>&1 || echo "missing example env for $compose"; done
```

Expected: no missing example env output for stacks that need an example file, except stacks such as `apps/downloads` if no example env existed before and validation is supplied via command-line placeholders.

## Task 3: Documentation And Migration Checklist

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `apps/docs/README.md`
- Create: `docs/migrations/2026-06-28-opn-158-appdata-root-migration.md`

- [ ] **Step 1: Update repo meaning of data roots**

Document:

```text
DATA_ROOT remains the user-data root for media libraries, downloads, photos, and broad read-only browsing mounts.
APPDATA_ROOT is the mutable container app-state root for service config, databases, generated state, cookies, queues, and certificate/config state.
Homepage is the deliberate exception: selected safe Homepage config is repo-managed under apps/utilities/homepage and mounted with ./homepage:/app/config.
```

- [ ] **Step 2: Add migration checklist**

Create a checklist covering these stacks and services:

```text
apps/utilities: glances, icloudpd, speedtest-tracker, n8n
apps/arr-stack: radarr, sonarr, prowlarr, bazarr, autoscan, cleanuparr
apps/media: jellyfin, jellyseerr
apps/downloads: qbittorrent, nzbget, flaresolverr, gluetun
apps/docs: paperless redis, postgres, data, media, consume, export
infra/proxy/nginx-proxy-manager: data, letsencrypt
infra/dns/adguard: work, conf
```

For each stack include this command shape, with service paths substituted:

```bash
sudo install -d -m 0750 /srv/appdata/<service>
sudo rsync -aHAX --numeric-ids --info=progress2 /data/configs/<service>/ /srv/appdata/<service>/
sudo find /srv/appdata/<service> -maxdepth 1 -ls
```

Include the backup/checkpoint reminder, ownership/permission verification, non-deploying compose validation, Komodo redeploy, smoke checks, and rollback by restoring the previous commit or previous compose mount and redeploying through Komodo.

## Task 4: Non-Deploying Validation

**Files:**
- Read/validate all modified compose files

- [ ] **Step 1: Validate YAML and Compose rendering**

Run `docker compose config` per stack with safe placeholder values. Example command shape:

```bash
env PUID=1000 PGID=1000 TZ=Pacific/Auckland DATA_ROOT=/data APPDATA_ROOT=/srv/appdata docker compose -f apps/media/compose.yml config >/tmp/opn-158-media.yml
```

Run equivalent commands for:

```text
apps/utilities/compose.yml
apps/arr-stack/compose.yml
apps/media/compose.yml
apps/downloads/compose.yml
apps/docs/compose.yml
infra/proxy/nginx-proxy-manager/compose.yml
infra/dns/adguard/compose.yml
identity/authentik/compose.yml
platform/komodo/mongo.compose.yaml
```

Include stack-specific placeholder env vars where Compose requires them.

- [ ] **Step 2: Confirm no live mutation occurred**

Do not run any of:

```bash
docker compose up
docker compose down
docker compose pull
docker compose restart
docker compose build
docker compose rm
docker compose stop
docker compose start
```

- [ ] **Step 3: Prepare final Linear update**

Summarize changed files, validation commands/results, migration checklist path, commit hash if committed, and remaining manual work: operator backup, data copy/sync, permission checks, Komodo redeploy, and service smoke checks.

## Self-Review

- Spec coverage: all OPN-158 acceptance criteria map to Tasks 1-4.
- Placeholder scan: no task uses TBD/TODO/fill-in-later language.
- Type/path consistency: `${APPDATA_ROOT}` is used for mutable app-state mounts; `${DATA_ROOT}` is kept for media/downloads/photos and Homepage read-only broad browsing; `./homepage:/app/config` remains the documented exception.
