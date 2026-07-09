# Recyclarr Profile Sync

## Scope

- Recyclarr owns selected TRaSH Guides quality profile, custom format, quality definition, media naming, and media management sync for Sonarr and Radarr.
- It does not replace Sonarr/Radarr request, download, import, or search behavior.
- It must remain internal-only on `media_net`; do not add `proxy_net`, Nginx Proxy Manager, Authentik, or AdGuard exposure for Recyclarr.
- Maintainerr remains responsible for watched-media cleanup.
- Seekarr and Mediastarr remain responsible for search automation evaluation.

## Runtime Configuration

- Service: `recyclarr` in `apps/arr-stack/compose.yml`
- Image: `ghcr.io/recyclarr/recyclarr:8`
- Container config path: `/config`
- Host appdata path: `${APPDATA_ROOT}/recyclarr`
- Repo starter config: `apps/arr-stack/config/recyclarr/recyclarr.yml`
- Internal Sonarr URL: `http://sonarr:8989`
- Internal Radarr URL: `http://radarr:7878`
- Initial Sonarr profile: `WEB-1080p` adopted into existing `HD - 720p/1080p`
- Initial Radarr profile: `HD Bluray + WEB` adopted into existing `HD - 720p/1080p`

Required real values belong in the untracked Arr stack `.env`:

```env
RECYCLARR_SONARR_API_KEY=change-me
RECYCLARR_RADARR_API_KEY=change-me
```

Do not commit real API keys.

## First Rollout

Before deployment, copy the starter config into appdata:

```bash
mkdir -p "${APPDATA_ROOT}/recyclarr"
cp apps/arr-stack/config/recyclarr/recyclarr.yml "${APPDATA_ROOT}/recyclarr/recyclarr.yml"
chown -R "${PUID}:${PGID}" "${APPDATA_ROOT}/recyclarr"
```

Deploy or redeploy the Arr stack through Komodo after the real `.env` keys are present.

Do not run a real sync first. Start with read-only and preview checks after the container exists:

```bash
docker logs recyclarr --tail=100
docker exec recyclarr recyclarr config list
docker exec recyclarr recyclarr sync --preview
```

Review the preview output before running a real sync. Apply to one selected Sonarr/Radarr profile first, confirm no manually important profile data was removed, then expand scope.

## Scheduled Sync

Leave scheduled sync disabled until the manual preview and first real sync are reviewed. If scheduled sync is enabled later, document the cron schedule and managed profiles in this file.
