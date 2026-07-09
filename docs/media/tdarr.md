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

## Deployment Prep Status (2026-07-10)

- [x] Host test library created: `/data/tdarr-test-library`
- [x] Host transcode cache created: `/data/tdarr-transcode-cache`
- [x] Host app-state directory created: `${APPDATA_ROOT}/tdarr` (`/srv/appdata/tdarr`)

## Runtime Validation Status

- Tdarr container is running.
- `docker inspect tdarr` confirms mounts:
  - `/data/tdarr-test-library` at `/media`
  - `/data/tdarr-transcode-cache` at `/temp`
  - `/srv/appdata/tdarr/server` at `/app/server`
  - `/srv/appdata/tdarr/configs` at `/app/configs`
  - `/srv/appdata/tdarr/logs` at `/app/logs`
- `docker logs tdarr --tail=80` shows server/node startup, node registration, and binary/scanner tests completing.
- NPM proxy host configured:
  - ID: `24`
  - Hostname: `tdarr.home.lab`
  - Upstream: `http://tdarr:8265`
  - Certificate: `6`
  - SSL forced: enabled
  - Websocket support: enabled
- Authentik configured:
  - Proxy provider: `tdarr` (`40`)
  - Application: `Tdarr` (`tdarr`)
  - Provider attached to embedded outpost.
- External route check:
  - `curl -k -I https://tdarr.home.lab` returns `HTTP/2 302` to `/outpost.goauthentik.io/start`, which is the expected unauthenticated proxy-auth redirect.
- Homepage entry is present in repo-managed config:
  - `https://tdarr.home.lab`
  - `siteMonitor: http://tdarr:8265`
- First Test Result not yet recorded. Run only against copied sample media in the test library.

## Task 3 Deployment Checklist (remaining)

- Run first safe Tdarr UI test through `https://tdarr.home.lab`.
- Add only copied sample files from `/data/tdarr-test-library`.
- Start with health checks before any transcode.
- Keep worker counts low.
- Record CPU/RAM/disk observations and Jellyfin playback result below.

## First Test Result

- Date: not yet run
- Test file count: not yet run
- Health check result: not yet run
- Transcode tested: not yet run
- CPU/RAM/disk observation: not yet run
- Jellyfin playback result: not yet run
- Keep status: not yet run
