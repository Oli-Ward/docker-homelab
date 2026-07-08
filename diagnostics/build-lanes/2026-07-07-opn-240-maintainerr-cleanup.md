# OPN-240 Maintainerr Cleanup Runbook

## Chosen Approach

Use Maintainerr for watched-media cleanup. Do not build custom OpenClaw, gateway, or filesystem deletion logic for the first version.

## Repo-Managed Wiring

- Compose service: `maintainerr` in `apps/arr-stack/compose.yml`
- Image: `ghcr.io/maintainerr/maintainerr:latest`
- App state: `${APPDATA_ROOT}/maintainerr:/opt/data`
- Runtime user: `${PUID}:${PGID}`
- Networks: `media_net`, `proxy_net`
- Internal URL: `http://maintainerr:6246`
- Health endpoint: `http://maintainerr:6246/api/health/ready`

## Required External UI Work

1. Appdata ownership: ensure `${APPDATA_ROOT}/maintainerr` exists and is writable by `${PUID}:${PGID}` before or immediately after the first deploy. For the recommended example values, that means `/srv/appdata/maintainerr` must be writable by `1000:1000`.
2. Komodo: redeploy the arr stack from this repo after review.
3. AdGuard: add or verify `maintainerr.home.lab`.
4. Nginx Proxy Manager: add a proxy host for `maintainerr.home.lab` to upstream `http://maintainerr:6246`.
5. Authentik: protect `https://maintainerr.home.lab` with proxy auth before normal browser use.
6. Homepage: verify the Maintainerr link and health monitor.

## Maintainerr Initial Setup

1. Open `https://maintainerr.home.lab` only after Authentik and NPM are configured.
2. Configure Jellyfin as the media server using internal Docker networking where possible.
3. Configure Radarr with `http://radarr:7878` and the real API key from Radarr UI or untracked secret storage.
4. Configure Sonarr with `http://sonarr:8989` and the real API key from Sonarr UI or untracked secret storage.
5. Configure Jellyseerr with `http://jellyseerr:5055` if request cleanup is enabled.
6. Do not commit API keys, tokens, exported Maintainerr state, or screenshots containing secrets.

## Conservative Cleanup Policy

Start with non-destructive collection review:

- Movies: watched in Jellyfin, older than the chosen minimum age, not in protected collections, then held in a Maintainerr collection for a grace period before action.
- TV: season-level cleanup for the first version. Do not delete individual watched episodes until the season-level behavior is proven too coarse.
- Exclusions: protect favorites, pinned/manual keep items, protected collections, and protected paths before enabling handling.
- Handling: configure Maintainerr to update Radarr/Sonarr monitoring or remove items in a way that prevents automatic re-download.

## Enablement Gate

Do not enable destructive handling until:

- Candidate collections have been reviewed.
- At least one movie and one TV-season sample match exactly as expected.
- Exclusions have been tested.
- A recent backup or recovery path exists for the relevant app state and media.

## Recovery

- Remove or adjust the Maintainerr rule or exclusion that selected the item.
- Re-monitor the item in Radarr/Sonarr only if it should be downloadable again.
- Re-request through Jellyseerr if appropriate.
- Restore from backup when the original deleted file is needed and re-download is not desired.

## Live Exposure Configuration

Applied on 2026-07-07 after the Maintainerr container was healthy:

- DNS: `maintainerr.home.lab` resolves to `192.168.1.103`; no explicit AdGuard rewrite was needed.
- Authentik: created proxy provider `maintainerr` with provider id `33`.
- Authentik: created application `Maintainerr` with slug `maintainerr`.
- Authentik: attached provider `33` to the embedded proxy outpost.
- Nginx Proxy Manager: created proxy host id `20`.
- Nginx Proxy Manager route: `https://maintainerr.home.lab` -> `http://maintainerr:6246`.
- Nginx Proxy Manager protection: copied the existing protected media-host `auth_request` advanced config pattern.

Verification evidence:

```text
getent hosts maintainerr.home.lab
192.168.1.103   maintainerr.home.lab

curl -k -I https://maintainerr.home.lab
HTTP/2 302
location: https://maintainerr.home.lab/outpost.goauthentik.io/start?rd=https://maintainerr.home.lab/

docker exec nginx-proxy-manager grep
/data/nginx/proxy_host/20.conf: server_name maintainerr.home.lab
/data/nginx/proxy_host/20.conf: auth_request /_auth
/data/nginx/proxy_host/20.conf: outpost.goauthentik

docker logs authentik-server
Loaded application host=maintainerr.home.lab name=maintainerr
```

Maintainerr integration and destructive rule setup remains intentionally manual. The local API was checked and the service is healthy, but no documented OpenAPI schema was exposed at `/api-json` or `/swagger-json`; do not create Jellyfin/Radarr/Sonarr/Jellyseerr integrations or deletion rules by guessed payloads.
