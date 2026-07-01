# OpenClaw Gateway

Dockerized FastAPI gateway for selected OpenClaw homelab capabilities.

## Boundary

OpenClaw calls this gateway over the media host LAN IP. The gateway calls upstream services over Docker networks and keeps upstream API keys on the media host.

For OPN-153, the gateway exposed only read-only Jellyfin and Jellyseerr media endpoints. OPN-156 adds read-only Sonarr and Radarr manager-library/status summaries for OpenClaw decisions that Jellyfin/Jellyseerr do not reliably provide, such as monitored state, missing/downloaded counts, filesystem path presence, and quality profile identifiers. OPN-211 adds one narrow Jellyseerr write endpoint for creating media requests after confirmation. OPN-212 adds one narrow Jellyfin completed-movie event endpoint that forwards rating-prompt events to the approved OpenClaw/n8n receiver.

The gateway does not expose qBittorrent, NZBGet, Prowlarr, Docker logs, Paperless, n8n, raw passthrough routes, the Docker socket, host networking, or media filesystem mounts. It also does not expose raw `/api/sonarr/*`, `/api/radarr/*`, or `/api/jellyseerr/*` passthrough paths.

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
POST /v1/media/jellyfin/watch-completed
GET /v1/media/jellyseerr/search?q=...
POST /v1/media/jellyseerr/requests
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

`POST /v1/media/jellyfin/watch-completed` accepts only completed movie watch events:

```json
{
  "event": "playback.stop",
  "item_id": "jellyfin-movie-1",
  "item_type": "movie",
  "title": "Alien",
  "year": 1979,
  "watched_at": "2026-07-01T07:10:00Z",
  "user_id": "oli-profile",
  "completed": true
}
```

The endpoint rejects non-movie payloads and partial playback events before forwarding. It sends only this minimal payload to the configured `N8N_JELLYFIN_RATING_PROMPT_PATH`:

```json
{
  "source": "jellyfin",
  "event": "watch_completed",
  "item_id": "jellyfin-movie-1",
  "title": "Alien",
  "year": 1979,
  "watched_at": "2026-07-01T07:10:00Z",
  "user_id": "oli-profile",
  "dedupe_key": "jellyfin-movie-1:2026-07-01T07:10:00Z"
}
```

Downstream OpenClaw/n8n handling should use `dedupe_key` to suppress repeat rating prompts. Rating storage remains outside this gateway; use the approved OpenClaw recommendation/media preference path or a follow-up ticket before persisting ratings somewhere new.

`POST /v1/media/jellyseerr/requests` accepts only this narrow request shape:

```json
{
  "media_type": "movie",
  "tmdb_id": 348,
  "note": "requested by OpenClaw after Oli confirmation",
  "dry_run": true
}
```

Use `media_type` as `movie` or `tv`. `tmdb_id` is the TMDB ID from Jellyseerr/search context. `note` is accepted for OpenClaw workflow context but is not forwarded to Jellyseerr because the upstream request API only needs media type and media ID.

Dry-run mode is the default and validates that the gateway can reach Jellyseerr without creating a request:

```json
{
  "status": "valid",
  "media_type": "movie",
  "tmdb_id": 348,
  "message": "Request target is valid; no request was created.",
  "request_id": null,
  "duplicate": false,
  "dry_run": true
}
```

Real request creation requires `dry_run: false`:

```json
{
  "status": "created",
  "media_type": "movie",
  "tmdb_id": 348,
  "message": "Jellyseerr request created.",
  "request_id": 77,
  "duplicate": false,
  "dry_run": false
}
```

Duplicate or already-requested upstream responses return a clean gateway result instead of raw Jellyseerr error details:

```json
{
  "status": "duplicate",
  "media_type": "movie",
  "tmdb_id": 348,
  "message": "Media has already been requested.",
  "request_id": null,
  "duplicate": true,
  "dry_run": false
}
```

OpenClaw policy: run with `dry_run: true` first. Before sending `dry_run: false`, OpenClaw must get explicit Oli confirmation for the exact title/media type/TMDB ID. The gateway does not approve or decline Jellyseerr requests; upstream auto-approval behavior depends only on the Jellyseerr API user's permissions.

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

These endpoints are fixed routes. The only media write routes are the narrow Jellyseerr request endpoint and the narrow Jellyfin completed-movie event endpoint above. Additional write actions, raw upstream passthrough, arbitrary path selection, and query-shaped upstream proxies require a later reviewed ticket.

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
N8N_WEBHOOK_BASE_URL=http://n8n:5678
N8N_JELLYFIN_RATING_PROMPT_PATH=/webhook/jellyfin-rating-prompt
UPSTREAM_TIMEOUT_SECONDS=5
```

`GATEWAY_AUTH_TOKEN` is the server-side variable consumed by this container. OpenClaw can store the same secret as `MEDIA_GATEWAY_TOKEN` on the client side, but Komodo must still provide `GATEWAY_AUTH_TOKEN` to the gateway stack.

Do not commit `.env` or real API keys. Jellyfin, Jellyseerr, Sonarr, and Radarr API keys and n8n webhook paths/secrets must stay on the media host in Komodo or the local deployment environment.

## Jellyfin Rating Prompt Rollout

External Jellyfin and n8n configuration is not managed by this repository. Use this repo change as the durable gateway configuration, then complete rollout in the relevant admin UIs:

1. Deploy or redeploy only the `openclaw-gateway` stack through Komodo.
2. Create or enable the n8n workflow at `/webhook/jellyfin-rating-prompt`.
3. Configure Jellyfin's webhook or notification plugin from the Jellyfin admin UI to POST only completed movie events for the intended profile to `/v1/media/jellyfin/watch-completed` with the gateway bearer token.
4. Smoke test with a simulated completed movie event before relying on real playback events.
5. Confirm downstream duplicate suppression uses the forwarded `dedupe_key`.

Example simulated event:

```bash
curl -sS -X POST "$GATEWAY_URL/v1/media/jellyfin/watch-completed" \
  -H "Authorization: Bearer $GATEWAY_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  --data-raw '{
    "event": "playback.stop",
    "item_id": "jellyfin-movie-1",
    "item_type": "movie",
    "title": "Alien",
    "year": 1979,
    "watched_at": "2026-07-01T07:10:00Z",
    "user_id": "oli-profile",
    "completed": true
  }'
```

Disable or roll back the event path by disabling the Jellyfin webhook/plugin entry, rotating or removing the gateway token used by that sender, or reverting the OPN-212 gateway changes and redeploying the gateway through Komodo. Disabling the webhook must not affect normal Jellyfin playback.

## Network

The service joins `media_net` for media services and `utilities_net` for the n8n rating-prompt webhook. It binds to the configured media host LAN IP and port:

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

To include a harmless Jellyseerr request dry-run probe:

```bash
CHECK_JELLYSEERR_REQUESTS=1 GATEWAY_URL=http://192.0.2.10:8088 GATEWAY_AUTH_TOKEN="$GATEWAY_AUTH_TOKEN" scripts/smoke-openclaw-gateway.sh
```

The Jellyseerr smoke probe posts a fixed `dry_run: true` payload and does not create a real request.

## Rollback

Use Komodo to redeploy the previous gateway configuration or image. If rolling back from Git, revert the route/client/docs changes for OPN-211 and redeploy only the `openclaw-gateway` stack through Komodo. Do not stop, recreate, pull, or restart containers directly from this repository unless that action has been explicitly approved.
