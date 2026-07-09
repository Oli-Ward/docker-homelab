# Backrest Restic Backup Management

Backrest manages restic repositories and schedules for selected homelab configuration and appdata. It complements existing manual encrypted appdata backups and is not a replacement for full-stack backups until restore procedures are proven.

## Initial scope

Backrest initially targets config/appdata only.

Include:

- `/userdata/docker-repo` (Compose and utility repository files)
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

Exclude:

- Bulk media libraries under `${DATA_ROOT}/media/*`
- `${DATA_ROOT}/downloads`
- `${DATA_ROOT}/transcode` cache
- Authentik PostgreSQL (handled by dedicated runbook)
- Komodo MongoDB (handled by dedicated runbook)
- Paperless appdata until a dedicated OPN is approved

## Repository layout

Backrest expects a mounted repository at `${BACKREST_RESTIC_REPO_HOST_PATH}`.

- Default in Compose: `/repos`
- Backrest config path: `${APPDATA_ROOT}/backrest`

## Scheduling and retention baseline

- Keep 7 daily snapshots
- Keep 4 weekly snapshots
- Keep 6 monthly snapshots
- Run periodic check and prune tasks from Backrest UI

## Restore test

A temporary restore test is required before Backrest is treated as trusted.

1. Verify an initial snapshot exists in the repository.
2. Restore a small, non-critical file to a temporary path inside the Backrest UI.
3. Validate file content and permissions.
4. Record snapshot ID, restore path, and result in the ticket.

## External exposure checklist

Create and verify these UI integrations before promoting Backrest to regular use:

- NPM host `backrest.home.lab` forwarding to `backrest:9898`.
- AuthentiK application/provider/outpost entry for `backrest`.
- Validate login/logout flow through AuthentiK.
- Keep Backrest config UI protected with internal network + AuthentiK.

## Scope verification checklist

- Confirm initial repository plan includes only the curated config/appdata roots.
- Confirm no full media or downloads directories are included in the first schedules.
- Confirm retention/check/prune values are persisted in the UI.
- Confirm restore target for test is temporary and not live appdata.
