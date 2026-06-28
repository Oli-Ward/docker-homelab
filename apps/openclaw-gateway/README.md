# OpenClaw Gateway

Dockerized FastAPI gateway for selected OpenClaw homelab capabilities.

## Boundary

OpenClaw calls this gateway over the media host LAN IP. The gateway calls upstream services over Docker networks and keeps upstream API keys on the media host.

For OPN-153, the gateway exposed only read-only Jellyfin and Jellyseerr media endpoints. OPN-156 adds read-only Sonarr and Radarr manager-library/status summaries for OpenClaw decisions that Jellyfin/Jellyseerr do not reliably provide, such as monitored state, missing/downloaded counts, filesystem path presence, and quality profile identifiers.

The gateway does not expose qBittorrent, NZBGet, Prowlarr, Docker logs, Paperless, n8n, raw passthrough routes, the Docker socket, host networking, or media filesystem mounts. It also does not expose raw `/api/sonarr/*` or `/api/radarr/*` passthrough paths.

OpenClaw should receive only:

```text
MEDIA_GATEWAY_URL=http://<media-host-ip>:8088
MEDIA_GATEWAY_TOKEN=<gateway token stored outside Git>
```

Do not give OpenClaw Jellyfin, Jellyseerr, Sonarr, or Radarr API keys.

## Endpoints

```text
GET /health
GET /v1/media/jellyfin/library
GET /v1/media/jellyfin/search?q=...
GET /v1/media/jellyseerr/search?q=...
GET /v1/media/sonarr/series
GET /v1/media/radarr/movies
```

`/health` is public and returns only:

```json
{ "status": "ok" }
```

All `/v1/...` endpoints require:

```text
Authorization: Bearer <token>
```

`GET /v1/media/sonarr/series` returns normalized series summaries:

```json
{
  "items": [
    {
      "id": "12",
      "tvdb_id": 12345,
      "title": "Severance",
      "year": 2022,
      "status": "continuing",
      "monitored": true,
      "path": "/tv/Severance",
      "quality_profile_id": 3,
      "statistics": {
        "season_count": 2,
        "episode_file_count": 10,
        "episode_count": 19,
        "total_episode_count": 19,
        "size_on_disk": 123456789
      },
      "tags": [4, 9]
    }
  ]
}
```

`GET /v1/media/radarr/movies` returns normalized movie summaries:

```json
{
  "items": [
    {
      "id": "34",
      "tmdb_id": 348,
      "title": "Alien",
      "year": 1979,
      "status": "released",
      "monitored": true,
      "has_file": true,
      "available": true,
      "path": "/movies/Alien (1979)",
      "quality_profile_id": 2,
      "statistics": {
        "movie_file_count": 1,
        "size_on_disk": 987654321
      },
      "tags": [7]
    }
  ]
}
```

These endpoints are read-only fixed routes. Write actions, raw upstream passthrough, arbitrary path selection, and query-shaped upstream proxies require a later reviewed ticket.

## Environment

Copy `example.env` to `.env` in Komodo or the deployment environment and replace placeholder values.

```dotenv
GATEWAY_BIND_HOST=192.0.2.10
GATEWAY_PORT=8088
GATEWAY_AUTH_TOKEN=change-me
JELLYFIN_URL=http://jellyfin:8096
JELLYFIN_API_KEY=change-me
JELLYSEERR_URL=http://jellyseerr:5055
JELLYSEERR_API_KEY=change-me
SONARR_URL=http://sonarr:8989
SONARR_API_KEY=change-me
RADARR_URL=http://radarr:7878
RADARR_API_KEY=change-me
UPSTREAM_TIMEOUT_SECONDS=5
```

`GATEWAY_AUTH_TOKEN` is the server-side variable consumed by this container. OpenClaw can store the same secret as `MEDIA_GATEWAY_TOKEN` on the client side, but Komodo must still provide `GATEWAY_AUTH_TOKEN` to the gateway stack.

Do not commit `.env` or real API keys. Sonarr/Radarr API keys must stay on the media host in Komodo or the local deployment environment.

## Network

The service joins only `media_net` for OPN-153. It binds to the configured media host LAN IP and port:

```yaml
ports:
  - "${GATEWAY_BIND_HOST}:${GATEWAY_PORT:-8088}:8080"
```

Restrict the host firewall so only the OpenClaw runtime IP can reach `GATEWAY_PORT`.

Example UFW shape:

```bash
sudo ufw allow from <openclaw-runtime-ip> to any port 8088 proto tcp
sudo ufw deny 8088/tcp
```

Use Komodo to deploy or redeploy this stack. Do not start, stop, pull, or recreate containers directly from this repository unless that action has been explicitly approved.

## Smoke Test

Run from a machine that can reach the gateway:

```bash
scripts/smoke-openclaw-gateway.sh http://192.0.2.10:8088 "$GATEWAY_AUTH_TOKEN"
```

Or use environment variables:

```bash
GATEWAY_URL=http://192.0.2.10:8088 GATEWAY_AUTH_TOKEN="$GATEWAY_AUTH_TOKEN" scripts/smoke-openclaw-gateway.sh
```

The script checks `/health` without auth, then checks an authenticated Jellyfin search without printing the token.

To include the Sonarr/Radarr endpoints in the smoke test after those upstreams are configured:

```bash
CHECK_ARR_ENDPOINTS=1 GATEWAY_URL=http://192.0.2.10:8088 GATEWAY_AUTH_TOKEN="$GATEWAY_AUTH_TOKEN" scripts/smoke-openclaw-gateway.sh
```
