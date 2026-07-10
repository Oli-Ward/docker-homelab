# Tdarr Removal Record

Tdarr was evaluated for media health checks and transcoding, then removed because it was too resource-heavy for this server.

## Decision

- Date: 2026-07-10
- Decision: remove Tdarr from the active media stack.
- Reason: too much expected CPU/RAM/storage pressure for this server.
- Scope: remove repo-managed service/dashboard config and remove NPM/AuthentiK access.

## Removed Active Config

- Docker Compose service removed from `apps/media/compose.yml`.
- Tdarr example env variables removed from `apps/media/example.env`.
- Homepage card removed from `apps/utilities/homepage/services.yaml`.
- README service catalog and safety note removed.
- NPM proxy host `tdarr.home.lab` removed.
- AuthentiK `Tdarr` application and `tdarr` proxy provider removed.

## Data Left Intact

These paths were intentionally not deleted:

- `${APPDATA_ROOT}/tdarr`
- `${DATA_ROOT}/tdarr-test-library`
- `${DATA_ROOT}/tdarr-transcode-cache`

Delete them only after separately confirming no useful config, logs, or test files need to be retained.

## Komodo Follow-Up

Use Komodo to redeploy the media stack and stop/remove the previously deployed Tdarr container. Do not run direct Docker removal commands unless explicitly approved.
