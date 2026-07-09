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

## Deployment Prep Status (2026-07-09)

- [x] Host test library created: `/data/tdarr-test-library`
- [x] Host transcode cache created: `/data/tdarr-transcode-cache`
- [ ] Host app-state directory created: `${APPDATA_ROOT}/tdarr` (`/srv/appdata/tdarr`)
  - Blocked in this environment: `/srv` is root-owned; creation requires privileged host access.

## Runtime Validation Status

- Tdarr container not currently deployed (`docker logs tdarr` / `docker inspect tdarr` return "no such container/object").
- NPM/AuthentiK/AdGuard external UI configuration not yet applied (manual deployment step pending).
- First Test Result not yet recorded (depends on deployment and manual safe test run).

## Task 3 Deployment Checklist (remaining)

- Run after Komodo media stack redeploy:
  - `docker logs tdarr --tail=100`
  - `docker inspect tdarr`
  - Confirm no restart loop, open UI on port `8265`, and mounts are:
    - `/data/tdarr-test-library` at `/media`
    - `/data/tdarr-transcode-cache` at `/temp`
- Configure `tdarr.home.lab`:
  - NPM route to `tdarr:8265`
  - AuthentiK app/provider/outpost for Tdarr
  - AdGuard record for `tdarr.home.lab`

## First Test Result

- Date: not yet run
- Test file count: not yet run
- Health check result: not yet run
- Transcode tested: not yet run
- CPU/RAM/disk observation: not yet run
- Jellyfin playback result: not yet run
- Keep status: not yet run
