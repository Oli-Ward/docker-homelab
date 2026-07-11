# OpenClaw Gateway

Dockerized FastAPI gateway for selected OpenClaw homelab capabilities.

## Boundary

OpenClaw calls this gateway over the media host LAN IP. The gateway calls upstream services over Docker networks and keeps upstream API keys on the media host.

For OPN-153, the gateway exposed only read-only Jellyfin and Seerr media endpoints. OPN-156 adds read-only Sonarr and Radarr manager-library/status summaries for OpenClaw decisions that Jellyfin/Seerr do not reliably provide, such as monitored state, missing/downloaded counts, filesystem path presence, and quality profile identifiers. OPN-210 refines the Jellyfin library endpoint into a normalized inventory contract with safe metadata and pagination controls. OPN-211 adds one narrow Seerr write endpoint for creating media requests after confirmation. OPN-212 adds one narrow Jellyfin watch-completion intake endpoint that forwards completed movie events to the configured OpenClaw/n8n rating-prompt workflow.

The gateway does not expose qBittorrent, NZBGet, Prowlarr, Docker logs, Paperless, raw n8n admin/API access, raw passthrough routes, the Docker socket, host networking, or media filesystem mounts. It also does not expose raw `/api/sonarr/*`, `/api/radarr/*`, `/api/seerr/*`, or arbitrary n8n webhook paths.

OpenClaw should receive only:

```text
MEDIA_GATEWAY_URL=http://<media-host-ip>:8088
MEDIA_GATEWAY_TOKEN=<gateway token stored outside Git>
```

Do not give OpenClaw Jellyfin, Seerr, Sonarr, Radarr, Ryot, or Plane API keys/admin tokens. Ryot admin access and Plane access belong in the gateway runtime only. OpenClaw should call the fixed gateway endpoints with the same gateway bearer token it already uses for Jellyfin, Seerr, Sonarr, Radarr, and Ryot.

## Endpoints

```text
GET /health
GET /v1/media/jellyfin/library?start_index=0&limit=50
GET /v1/media/jellyfin/search?q=...
GET /v1/media/seerr/search?q=...
POST /v1/media/seerr/requests
POST /v1/media/jellyfin/watch-completed
GET /v1/media/sonarr/series
GET /v1/media/radarr/movies
GET /v1/media/ryot/probe
POST /v1/automation/n8n/openclaw-smoke
POST /v1/workflow/plane/webhook
GET /v1/workflow/plane/webhook/queue
POST /v1/workflow/plane/webhook/dispatch?limit=10
GET /v1/workflow/plane/projects
GET /v1/workflow/plane/projects/{project_id}/states
GET /v1/workflow/plane/projects/{project_id}/labels
GET /v1/workflow/plane/search?q=...
GET /v1/workflow/plane/projects/{project_id}/work-items
GET /v1/workflow/plane/projects/{project_id}/work-items/{work_item_id}
POST /v1/workflow/plane/projects/{project_id}/work-items
PATCH /v1/workflow/plane/projects/{project_id}/work-items/{work_item_id}
POST /v1/workflow/plane/projects/{project_id}/work-items/{work_item_id}/comments
```

`/health` is public and returns only:

```json
{ "status": "ok" }
```

All `/v1/...` endpoints except `POST /v1/workflow/plane/webhook` require:

```text
Authorization: Bearer <token>
```

Plane workflow endpoints call the self-hosted Plane API with a Plane API key stored only in the gateway runtime environment:

```env
PLANE_API_BASE_URL=http://192.168.1.103:8085
PLANE_API_KEY=<stored outside Git>
PLANE_WORKSPACE_SLUG=<workspace slug>
PLANE_DEFAULT_PROJECT_ID=<optional project UUID>
PLANE_WEBHOOK_SECRET=<stored outside Git, copied from Plane webhook setup>
PLANE_WEBHOOK_QUEUE_PATH=/app/state/plane-webhooks/events.jsonl
PLANE_WEBHOOK_DEDUPE_PATH=<optional sidecar path; defaults next to queue>
PLANE_WEBHOOK_IGNORED_ACTOR_IDS=<optional comma-separated Plane user IDs>
N8N_PLANE_WEBHOOK_DISPATCH_PATH=/webhook/plane-openclaw-dispatch
```

The gateway authenticates to Plane with `X-API-Key` and returns normalized project, state, label, work-item, and comment responses. It does not return the Plane API key or raw upstream error bodies. Write routes are intentionally narrow and currently support only the fields OpenClaw needs for initial ticket creation, state updates, labels, assignees, parent links, and progress comments.

`POST /v1/workflow/plane/webhook` is the Plane webhook ingress endpoint. It does not use the gateway bearer token because Plane authenticates each delivery with `X-Plane-Signature`; configure the webhook secret in `PLANE_WEBHOOK_SECRET`.

Expected Plane headers:

```text
X-Plane-Delivery: <delivery UUID>
X-Plane-Event: <event name>
X-Plane-Signature: <HMAC-SHA256 hex digest>
```

The gateway validates the signature and returns a small acknowledgement:

```json
{
  "accepted": true,
  "correlation_id": "plane:delivery-uuid",
  "delivery_id": "delivery-uuid",
  "event": "issue",
  "action": "update",
  "resource_id": "work-item-uuid",
  "webhook_id": "webhook-uuid",
  "queued": true,
  "duplicate": false
}
```

After signature validation, the gateway writes one normalized JSONL record per new Plane delivery to `PLANE_WEBHOOK_QUEUE_PATH` and logs the same `correlation_id` with delivery, event, action, resource, webhook, queued, duplicate, and actor fields. Duplicate `X-Plane-Delivery` values return `queued: false` and `duplicate: true` without appending another queue record. The queue is mounted under `${APPDATA_ROOT}/openclaw-gateway` in Compose; confirm this appdata path is backed up or checkpointed before live deployment.

Set `PLANE_WEBHOOK_IGNORED_ACTOR_IDS` to comma-separated Plane user IDs for gateway, OpenClaw write-back, Codex/ChatGPT, or n8n automation actors. Matching deliveries are acknowledged with `queued: false`, `suppressed: true`, and `suppressed_reason: "ignored_actor"` without being written to the queue. This prevents OpenClaw-originated Plane updates from looping back into new OpenClaw work.

`GET /v1/workflow/plane/webhook/queue` is an authenticated, read-only diagnostics endpoint for the ingress queue:

```json
{
  "configured": true,
  "queue_path": "/app/state/plane-webhooks/events.jsonl",
  "dedupe_path": "/app/state/plane-webhooks/events.jsonl.seen",
  "queued_count": 2,
  "dedupe_count": 2,
  "malformed_count": 0,
  "last_delivery_id": "delivery-uuid",
  "last_correlation_id": "plane:delivery-uuid"
}
```

It never returns raw Plane payloads, webhook signatures, or secrets. To include this in the gateway smoke script, run `CHECK_PLANE_WEBHOOK_QUEUE=1 scripts/smoke-openclaw-gateway.sh`.

`POST /v1/workflow/plane/webhook/dispatch?limit=10` is an authenticated dispatcher for queued Plane events. It sends pending normalized events to `N8N_PLANE_WEBHOOK_DISPATCH_PATH` and records successfully dispatched delivery IDs in a sidecar file next to the queue. If n8n times out or returns an error, the failed delivery is not marked dispatched, so the next dispatch call retries it. The endpoint returns only dispatch counts and delivery IDs:

```json
{
  "dispatched_count": 2,
  "pending_count": 0,
  "delivery_ids": ["delivery-1", "delivery-2"],
  "failed_delivery_id": null
}
```

The repo-managed n8n workflow template lives at `apps/utilities/n8n/workflows/plane-openclaw-dispatch.workflow.json` and calls `apps/utilities/n8n/scripts/send-plane-openclaw-dispatch.sh`. Live automation still requires importing/enabling that workflow in n8n, confirming the `/opt/n8n-scripts` mount from the utilities stack, configuring the OpenClaw SSH environment and `OPENCLAW_PLANE_DISPATCH_COMMAND`, and then smoke testing with a disabled/test Plane webhook before Komodo deployment.

The n8n sender forwards only the normalized dispatch record to OpenClaw:

```json
{
  "source": "plane",
  "event": "issue",
  "action": "update",
  "correlation_id": "plane:delivery-uuid",
  "delivery_id": "delivery-uuid",
  "resource_id": "work-item-uuid",
  "webhook_id": "webhook-uuid",
  "actor_id": "plane-user-uuid",
  "received_at": "2026-07-11T08:45:00.000Z"
}
```

It does not forward raw Plane payloads, webhook signatures, or gateway tokens.

Example Plane work-item create request:

```json
{
  "name": "Wire Plane adapter into OpenClaw",
  "description_html": "<p>Created by OpenClaw after confirmation.</p>",
  "state_id": "state-uuid",
  "priority": "medium",
  "label_ids": ["label-uuid"],
  "assignee_ids": [],
  "parent_id": null
}
```

Example Plane comment request:

```json
{
  "comment_html": "<p>OpenClaw accepted this ticket and started work.</p>"
}
```

`GET /v1/media/jellyfin/library` returns a read-only, normalized Jellyfin inventory for OpenClaw availability and recommendation checks:

```json
{
  "items": [
    {
      "id": "jf-item-id",
      "type": "movie",
      "title": "Alien",
      "year": 1979,
      "overview": "Space horror",
      "available": true,
      "request_status": null,
      "library": "Movies",
      "runtime_minutes": 117,
      "genres": ["Horror", "Sci-Fi"]
    }
  ],
  "pagination": {
    "mode": "window",
    "start_index": 0,
    "limit": 50,
    "total": 147
  }
}
```

Use `start_index` and `limit` to page through large libraries. `limit` is optional and capped at 500 by the gateway. Without `limit`, the gateway returns Jellyfin's full response and marks pagination as:

```json
{
  "mode": "full_response",
  "start_index": 0,
  "limit": null,
  "total": 147
}
```

The Jellyfin inventory endpoint is not a raw passthrough. It returns only normalized presentation metadata and does not expose Jellyfin API keys, raw media filesystem paths, Docker access, arbitrary Jellyfin routes, or user watch history.

`POST /v1/media/seerr/requests` accepts only this narrow request shape:

```json
{
  "media_type": "movie",
  "tmdb_id": 348,
  "note": "requested by OpenClaw after Oli confirmation",
  "dry_run": true
}
```

Use `media_type` as `movie` or `tv`. `tmdb_id` is the TMDB ID from Seerr/search context. `note` is accepted for OpenClaw workflow context but is not forwarded to Seerr because the upstream request API only needs media type and media ID.

Dry-run mode is the default and validates that the gateway can reach Seerr without creating a request:

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
  "message": "Seerr request created.",
  "request_id": 77,
  "duplicate": false,
  "dry_run": false
}
```

Duplicate or already-requested upstream responses return a clean gateway result instead of raw Seerr error details:

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

OpenClaw policy: run with `dry_run: true` first. Before sending `dry_run: false`, OpenClaw must get explicit Oli confirmation for the exact title/media type/TMDB ID. The gateway does not approve or decline Seerr requests; upstream auto-approval behavior depends only on the Seerr API user's permissions.

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

`GET /v1/media/ryot/probe` verifies that the gateway can reach Ryot's GraphQL endpoint with the gateway-held Ryot admin token. It sends only a fixed `__typename` query and does not expose raw GraphQL passthrough:

```json
{
  "status": "ok",
  "service": "ryot",
  "typename": "QueryRoot"
}
```

Ryot media-state lookup is not exposed yet. Upstream Ryot v10 has useful GraphQL fields such as `metadataSearch`, `metadataLookup`, `metadataDetails`, `userMetadataList`, and `userMetadataDetails`, but no single external-ID media-state field was verified for this slice. Add a separate fixed endpoint only after the exact lookup sequence and response shape are designed and tested.

These endpoints are fixed routes. The only media write routes are the narrow Seerr request endpoint and the narrow Jellyfin completed-movie event endpoint above. Additional write actions, raw upstream passthrough, arbitrary path selection, and query-shaped upstream proxies require a later reviewed ticket.

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
SEERR_URL=http://seerr:5055
SEERR_API_KEY=change-me
SONARR_URL=http://sonarr:8989
SONARR_API_KEY=change-me
RADARR_URL=http://radarr:7878
RADARR_API_KEY=change-me
RYOT_URL=http://ryot:8000
RYOT_ADMIN_ACCESS_TOKEN=change-me
PLANE_API_BASE_URL=http://192.168.1.103:8085
PLANE_API_KEY=change-me
PLANE_WORKSPACE_SLUG=your-plane-workspace
PLANE_DEFAULT_PROJECT_ID=
PLANE_WEBHOOK_SECRET=change-me
PLANE_WEBHOOK_QUEUE_PATH=/app/state/plane-webhooks/events.jsonl
PLANE_WEBHOOK_DEDUPE_PATH=
PLANE_WEBHOOK_IGNORED_ACTOR_IDS=
N8N_WEBHOOK_BASE_URL=http://n8n:5678
N8N_OPENCLAW_SMOKE_PATH=/webhook/openclaw-smoke
N8N_JELLYFIN_RATING_PROMPT_PATH=/webhook/jellyfin-rating-prompt
N8N_PLANE_WEBHOOK_DISPATCH_PATH=/webhook/plane-openclaw-dispatch
UPSTREAM_TIMEOUT_SECONDS=15
```

`GATEWAY_AUTH_TOKEN` is the server-side variable consumed by this container. OpenClaw can store the same secret as `MEDIA_GATEWAY_TOKEN` on the client side, but Komodo must still provide `GATEWAY_AUTH_TOKEN` to the gateway stack.

Do not commit `.env` or real API keys. Jellyfin, Seerr, Sonarr, Radarr, Ryot, and Plane API keys and any n8n webhook secrets must stay on the media host in Komodo or the local deployment environment.

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

To include a harmless Seerr request dry-run probe:

```bash
CHECK_SEERR_REQUESTS=1 GATEWAY_URL=http://192.0.2.10:8088 GATEWAY_AUTH_TOKEN="$GATEWAY_AUTH_TOKEN" scripts/smoke-openclaw-gateway.sh
```

The Seerr smoke probe posts a fixed `dry_run: true` payload and does not create a real request.

To include the n8n smoke route after the media-host workflow exists:

```bash
CHECK_N8N_SMOKE=1 GATEWAY_URL=http://192.0.2.10:8088 GATEWAY_AUTH_TOKEN="$GATEWAY_AUTH_TOKEN" scripts/smoke-openclaw-gateway.sh
```

Capture non-secret evidence from gateway and n8n logs showing the generated request ID and success result. Do not paste token values into diagnostics or Linear.

## Rollback

Use Komodo to redeploy the previous gateway configuration or image. If rolling back from Git, revert the route/client/docs changes for OPN-211 and redeploy only the `openclaw-gateway` stack through Komodo. Do not stop, recreate, pull, or restart containers directly from this repository unless that action has been explicitly approved.
