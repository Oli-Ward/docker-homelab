# OpenClaw Gateway

Dockerized FastAPI gateway for selected OpenClaw homelab capabilities.

## Boundary

OpenClaw calls this gateway over the media host LAN IP. The gateway calls upstream services over Docker networks and keeps upstream API keys on the media host.

For OPN-153, the gateway exposed only read-only Jellyfin and Jellyseerr media endpoints. OPN-156 adds read-only Sonarr and Radarr manager-library/status summaries for OpenClaw decisions that Jellyfin/Jellyseerr do not reliably provide, such as monitored state, missing/downloaded counts, filesystem path presence, and quality profile identifiers. OPN-211 adds one narrow Jellyseerr write endpoint for creating media requests after confirmation. OPN-212 adds one narrow Jellyfin watch-completion intake endpoint that forwards completed movie events to the configured OpenClaw/n8n rating-prompt workflow.

The gateway does not expose qBittorrent, NZBGet, Prowlarr, Docker logs, Paperless, raw n8n admin/API access, raw passthrough routes, the Docker socket, host networking, or media filesystem mounts. It also does not expose raw `/api/sonarr/*`, `/api/radarr/*`, `/api/jellyseerr/*`, or arbitrary n8n webhook paths.

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
POST /v1/media/jellyseerr/requests
POST /v1/media/jellyfin/watch-completed
GET /v1/media/sonarr/series
GET /v1/media/radarr/movies
POST /v1/automation/n8n/openclaw-smoke
```

`/health` is public and returns only:

```json
{ "status": "ok" }
```

All `/v1/...` endpoints require:

```text
Authorization: Bearer <token>
```

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

`POST /v1/media/jellyfin/watch-completed` accepts only completed movie events. It rejects TV episodes, shows, and partial playback events before forwarding anything:

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

The gateway derives a dedupe key from `item_id` and `watched_at`, then forwards only this minimal payload to the configured `N8N_JELLYFIN_RATING_PROMPT_PATH`:

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

The expected n8n/OpenClaw workflow response is:

```json
{
  "ok": true,
  "workflow": "jellyfin-rating-prompt",
  "received": true,
  "dedupe_key": "jellyfin-movie-1:2026-07-01T07:10:00Z"
}
```

The gateway response is:

```json
{
  "status": "forwarded",
  "dedupe_key": "jellyfin-movie-1:2026-07-01T07:10:00Z",
  "forwarded": true,
  "message": "Completed movie event forwarded for rating prompt."
}
```

Duplicate suppression happens in the OpenClaw/n8n rating-prompt workflow or downstream recommendation store using the forwarded `dedupe_key`; the gateway is intentionally stateless.

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

`POST /v1/automation/n8n/openclaw-smoke` is a no-op automation smoke route for OPN-59. It forwards only this fixed payload to the configured n8n webhook:

```json
{ "source": "openclaw", "test": true, "request_id": "<generated-request-id>" }
```

The expected n8n workflow response is:

```json
{ "ok": true, "workflow": "openclaw-smoke", "received": true }
```

The gateway returns that shape plus the generated `request_id`. It must not expose raw n8n credentials, admin APIs, arbitrary webhook paths, or workflow mutation.

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
N8N_OPENCLAW_SMOKE_PATH=/webhook/openclaw-smoke
N8N_JELLYFIN_RATING_PROMPT_PATH=/webhook/jellyfin-rating-prompt
UPSTREAM_TIMEOUT_SECONDS=5
```

`GATEWAY_AUTH_TOKEN` is the server-side variable consumed by this container. OpenClaw can store the same secret as `MEDIA_GATEWAY_TOKEN` on the client side, but Komodo must still provide `GATEWAY_AUTH_TOKEN` to the gateway stack.

Do not commit `.env` or real API keys. Jellyfin, Jellyseerr, Sonarr, and Radarr API keys and any n8n webhook secrets must stay on the media host in Komodo or the local deployment environment.

## n8n Smoke Workflow

The n8n workflow lives in the media-host n8n app state under `${APPDATA_ROOT}/n8n`, not in this repository. With the example environment this resolves to `/srv/appdata/n8n`.

Required workflow:

```text
Webhook path: openclaw-smoke
Method: POST
Response: static JSON body
```

Static response:

```json
{ "ok": true, "workflow": "openclaw-smoke", "received": true }
```

The workflow should record enough execution metadata to confirm the request ID, but it must not log gateway tokens or add media-app, document-store, external-account, downloader, indexer, Docker socket, or host-control actions.

Rollback is to disable or delete the `openclaw-smoke` workflow and remove or rotate any token or webhook path used for the test.

## Jellyfin Rating Prompt Workflow

The Jellyfin event source is not repo-managed. Configure it in the Jellyfin admin UI with the available webhook or notification plugin after the gateway stack is deployed through Komodo.

Required rollout:

1. Deploy the updated `openclaw-gateway` stack through Komodo.
2. Create or enable the n8n workflow at `/webhook/jellyfin-rating-prompt`.
3. Configure the Jellyfin webhook/notification plugin to POST only completed movie events for the intended Jellyfin user/profile to `http://<media-host-ip>:8088/v1/media/jellyfin/watch-completed`.
4. Set the webhook `Authorization` header to `Bearer <gateway token>` without exposing Jellyfin admin credentials to OpenClaw.
5. Smoke test the gateway endpoint with a simulated movie completion before relying on real playback events.

Smoke test shape:

```bash
curl -fsS \
  -H "Authorization: Bearer $GATEWAY_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "playback.stop",
    "item_id": "jellyfin-movie-1",
    "item_type": "movie",
    "title": "Alien",
    "year": 1979,
    "watched_at": "2026-07-01T07:10:00Z",
    "user_id": "oli-profile",
    "completed": true
  }' \
  http://<media-host-ip>:8088/v1/media/jellyfin/watch-completed
```

Rollback is to disable the Jellyfin webhook/plugin entry, disable the n8n `jellyfin-rating-prompt` workflow, or rotate/remove the gateway token. This does not affect normal Jellyfin playback.

## Network

The service joins `media_net` for media services and `utilities_net` for the scoped n8n smoke and rating-prompt webhooks. It binds to the configured media host LAN IP and port:

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

To include the n8n smoke route after the media-host workflow exists:

```bash
CHECK_N8N_SMOKE=1 GATEWAY_URL=http://192.0.2.10:8088 GATEWAY_AUTH_TOKEN="$GATEWAY_AUTH_TOKEN" scripts/smoke-openclaw-gateway.sh
```

Capture non-secret evidence from gateway and n8n logs showing the generated request ID and success result. Do not paste token values into diagnostics or Linear.

## Rollback

Use Komodo to redeploy the previous gateway configuration or image. If rolling back from Git, revert the route/client/docs changes for OPN-211 and redeploy only the `openclaw-gateway` stack through Komodo. Do not stop, recreate, pull, or restart containers directly from this repository unless that action has been explicitly approved.
