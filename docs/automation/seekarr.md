# Seekarr Evaluation

## Upstream Verification

- Repository: https://github.com/tumeden/seekarr
- Official image: `ghcr.io/tumeden/seekarr:latest` (README also documents `tumeden/seekarr:latest`)
- Selected tag: `latest`, with latest GitHub release noted as `v0.5.0` on 2026-06-30
- License: MIT
- Latest commit: `4b24d3929dd5d4f618282b63d57d785bc80f3ddd` committed 2026-07-06 (`2026-07-06T20:04:03Z` via GitHub API)
- Latest commit date: 2026-07-06
- Maintenance check: recent activity and releases are present (`v0.5.0` and updates through 2026-07-06), so it is not clearly abandoned.
- Persistence path: upstream Docker examples mount host data to `/data`.
- Configuration model: upstream documents first-run web UI configuration for Radarr/Sonarr instances and API keys, not Compose environment variables.

## Supported Integrations

- Sonarr: documented as first-class companion target
- Radarr: documented as first-class companion target
- Jellyfin/Plex: not documented in upstream README/docker examples
- Seerr/Jellyseerr: not documented in upstream README/docker examples

## Risky Actions

- Missing-item retry searches (repeat checks)
- Better release search (searches for higher-quality re-queries)
- Per-instance scheduled searches
- Writes/search actions to Sonarr/Radarr APIs (does not advertise destructive deletes/cleanup actions in docs)

## Safety Features

- Rate caps
- Quiet hours
- Retry delay and release delay controls
- Per-instance schedules
- Web UI authentication and encrypted Arr API keys in SQLite
- No documented dry-run mode or `DRY_RUN` environment variable was found in upstream README examples.

## Fit Decision

Seekarr overlaps with Mediastarr for missing-content and better-release searching. It can help automate repeat lookups without replacing Sonarr/Radarr.

Decision:

- Install status: verified and approved for internal-only evaluation
- Initial exposure: internal only
- Initial automation: manual UI setup only; keep schedules disabled or conservative until one test search is reviewed
- Replacement/companion decision vs Mediastarr: pending OPN-246 comparison

## Initial Runtime Policy

- Expose the UI through Nginx Proxy Manager and Authentik only; do not publish container ports directly.
- Configure Radarr/Sonarr from the web UI using internal URLs: `http://radarr:7878` and `http://sonarr:8989`.
- Do not add Arr API keys to Compose env; Seekarr stores them encrypted in its SQLite data under `${APPDATA_ROOT}/seekarr`.
- Because no upstream dry-run mode is documented, avoid enabling scheduled repeat searches until one manual/test search is reviewed.
- Do not enable automatic deletions, quality profile mutation, watch/unwatch actions, or scheduled repeat searches until one manual/test search is reviewed.
- Recyclarr remains owner of TRaSH/profile/custom-format sync.
- Maintainerr remains owner of watched-media cleanup.
- Seerr remains owner of user request workflows.

## UI Exposure Decision

- UI exists: yes
- UI port: `8788`
- Native auth exists: yes
- Exposure approved by user: yes

## External UI Configuration

Nginx Proxy Manager:

- Domain: `seekarr.home.lab`
- Scheme: `http`
- Forward hostname: `seekarr`
- Forward port: `8788`
- SSL: use the existing `home.lab` certificate policy
- Websockets: enable if the UI requires it during runtime verification

Authentik:

- Application name: `Seekarr`
- Protect the NPM route with the existing Authentik proxy/outpost pattern used for media management apps.
- Keep Seekarr native web UI authentication enabled unless it conflicts during runtime verification.

Homepage:

- Entry added under Download Management.
- URL: `https://seekarr.home.lab`
- Monitor target: `http://seekarr:8788`

## Seekarr vs Mediastarr Decision

- Preferred tool: pending OPN-246 comparison
- Reason: both tools target repeat search behavior for Sonarr/Radarr; Seekarr adds quiet-hour/rate-limit controls, web UI, and encrypted Arr API key storage, while Mediastarr appears to provide similar intent through the `kroeberd/mediastarr` image.
- Services to keep installed: keep Seekarr internal-only while OPN-246 comparison is finalized; keep existing Sonarr/Radarr and Maintainerr.
- Services to remove later: none yet (pending comparison outcome and manual/test search review).
