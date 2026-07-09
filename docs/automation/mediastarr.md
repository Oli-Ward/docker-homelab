# Mediastarr Evaluation

## Upstream Verification

- Repository: https://github.com/kroeberd/mediastarr
- Official image: `kroeberd/mediastarr:latest` per upstream README
- License: MIT (repository license metadata)
- Selected tag: `latest` (floating) initially
- Latest release: `v7.1.12` (2026-05-17)
- Latest commit: `382551879fa47f93e9ab35b190ce2ea13fbf61d3` (2026-05-17T12:44:26Z)
- Supported integrations: Sonarr, Radarr, Lidarr (experimental), web hooks, webhook trigger endpoint
- Risky actions to review before enabling writes: quality-profile mutation, monitor changes, delete/unmonitor behavior, webhook side effects
- Storage path from upstream Docker Compose example: `${APPDATA_ROOT}/mediastarr:/data`

## Fit Decision

- Install status: **approved for internal-first evaluation**
- Initial exposure: **internal only** on `media_net`
- Initial automation: **dry-run/manual validation only**
- Replacement/companion decision vs Seekarr: pending OPN-247 comparison

## Initial Runtime Policy

- Keep internal-only on `media_net` for first evaluation.
- Do not schedule automatic searches until one manual dry-run/test search is reviewed.
- Do not enable delete, unmonitor, or quality-profile mutation behavior.
- Recyclarr remains owner of TRaSH/profile/custom-format sync.
- Maintainerr remains owner of watched-media cleanup.

## UI Exposure Decision

- UI exists: yes
- UI port: `7979`
- Native auth exists: optional (`MEDIASTARR_PASSWORD` in docs)
- Exposure approved by user: yes

## External UI Checklist

- NPM host: create `mediastarr.home.lab` proxy host -> `mediastarr:7979`
- Authentik application/provider/outpost entry: `Mediastarr`.
- AdGuard DNS record: `mediastarr.home.lab` points to NPM host.
- Homepage entry added under Download Management.
