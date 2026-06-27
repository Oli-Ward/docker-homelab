# OpenClaw Gateway Design

## Linear Issue

OPN-153: MEDIA: Build Docker media API gateway for OpenClaw

## Goal

Build a Dockerized FastAPI gateway that OpenClaw can call for selected homelab capabilities without giving OpenClaw direct access to upstream service networks or upstream API keys.

The first release implements a read-only media capability for Jellyfin and Jellyseerr. Sonarr and Radarr are deferred to OPN-156. Docker logs, Paperless, and n8n are future capability packs and are out of scope for OPN-153.

## Architecture

The gateway lives in a new independent stack:

```text
apps/openclaw-gateway/
  compose.yml
  example.env
  README.md
  openclaw-gateway/
    Dockerfile
    pyproject.toml
    openclaw_gateway/
      main.py
      settings.py
      auth.py
      routers/
        media.py
      clients/
        jellyfin.py
        jellyseerr.py
      schemas/
        media.py
    tests/
```

The Python package is named `openclaw_gateway` because the long-term service is an OpenClaw internal capability gateway, not only a media gateway.

For OPN-153, the container joins only the external `media_net` Docker network. It does not join `proxy_net`, does not sit behind Nginx Proxy Manager or Authentik, does not use host networking, does not mount `/var/run/docker.sock`, and does not mount media directories.

## Network Boundary

OpenClaw calls the gateway over the media host LAN address:

```text
OpenClaw Ubuntu runtime
  -> http://<media-host-ip>:8088
  -> openclaw-gateway container
  -> Jellyfin and Jellyseerr over media_net
```

The Compose port mapping is configurable:

```yaml
ports:
  - "${GATEWAY_BIND_HOST}:${GATEWAY_PORT:-8088}:8080"
```

The host firewall should allow the gateway port only from the OpenClaw runtime IP. This firewall rule is an operational requirement, not something Compose can enforce by itself.

## HTTP API

First-pass routes:

```text
GET /health
GET /v1/media/jellyfin/library
GET /v1/media/jellyfin/search?q=...
GET /v1/media/jellyseerr/search?q=...
```

`GET /health` is unauthenticated and returns only basic liveness:

```json
{ "status": "ok" }
```

All `/v1/...` routes require:

```text
Authorization: Bearer <token>
```

Jellyfin and Jellyseerr search stay separate. OPN-153 does not include a combined `/v1/media/search` endpoint because merging library availability and request availability would require product decisions around IDs, titles, years, media types, and status precedence.

## Response Policy

The gateway returns normalized summaries, not raw upstream payloads.

Jellyfin search returns media items shaped around fields OpenClaw needs, such as:

```json
{
  "items": [
    {
      "id": "abc",
      "type": "movie",
      "title": "Alien",
      "year": 1979,
      "overview": "Summary text",
      "available": true
    }
  ]
}
```

Jellyseerr search returns discoverable media and status information in the same normalized style, including media type, title, year, availability, and request status when the upstream response provides it.

Raw passthrough routes are explicitly forbidden. The gateway must not expose routes such as:

```text
/api/jellyfin/*
/api/jellyseerr/*
```

## Configuration

Gateway-side env vars:

```text
GATEWAY_BIND_HOST=192.168.1.103
GATEWAY_PORT=8088
GATEWAY_AUTH_TOKEN=change-me
JELLYFIN_URL=http://jellyfin:8096
JELLYFIN_API_KEY=change-me
JELLYSEERR_URL=http://jellyseerr:5055
JELLYSEERR_API_KEY=change-me
UPSTREAM_TIMEOUT_SECONDS=5
```

Secrets live only in `apps/openclaw-gateway/.env`, which is ignored by Git through the existing `.env` ignore rule. `example.env` documents variable names with placeholder values only.

The app validates required Jellyfin and Jellyseerr configuration at startup and fails fast if required values are missing. This avoids a half-configured security boundary.

## Auth

OPN-153 uses one static bearer token.

The gateway container env var is `GATEWAY_AUTH_TOKEN`. OpenClaw may use whatever client-side env var name it already expects, as long as it sends the token as:

```text
Authorization: Bearer <token>
```

The gateway must not log bearer tokens, upstream API keys, or full request headers.

## Upstream Behavior

The gateway uses short upstream request timeouts, defaulting to:

```text
UPSTREAM_TIMEOUT_SECONDS=5
```

There are no automatic retries in OPN-153. OpenClaw can retry intentionally if needed.

Timeouts return a normalized `504` response. Other upstream failures return normalized `502` responses where appropriate.

## Logging

The gateway logs enough for debugging without becoming a media activity log.

Allowed log fields:

- HTTP method
- route path
- response status
- latency
- upstream service name
- upstream failure status or error class

Forbidden log fields:

- `Authorization` headers
- upstream API keys
- raw upstream payloads
- full normalized response bodies
- private media payload details beyond what is needed to diagnose an error class

The default log level is `INFO`.

## Testing

The FastAPI app has focused `pytest` coverage for:

- `/health` works without auth.
- `/v1/...` endpoints reject missing bearer tokens.
- `/v1/...` endpoints reject invalid bearer tokens.
- Jellyfin client code normalizes mocked upstream payloads.
- Jellyseerr client code normalizes mocked upstream payloads.
- Missing required configuration fails settings validation or startup.

The repository also includes a small smoke script:

```text
scripts/smoke-openclaw-gateway.sh
```

The script accepts the gateway URL and token as arguments or env vars, calls `/health`, then calls one authenticated search endpoint. It must not print the token.

## Documentation

`apps/openclaw-gateway/README.md` documents:

- network boundaries
- required env vars
- allowed endpoints
- explicitly forbidden passthrough behavior
- firewall guidance for allowing only the OpenClaw runtime IP
- Komodo deployment expectations
- smoke-test usage

## Deferred Work

Deferred from OPN-153:

- Sonarr/Radarr read-only endpoints, tracked by OPN-156.
- write endpoints for Jellyseerr media requests.
- qBittorrent, NZBGet, and Prowlarr access.
- Docker log access.
- Paperless capability endpoints.
- n8n capability endpoints.
- a unified `/v1/media/search` route.

Each future capability pack should be reviewed as its own ticket because it may require additional Docker networks, credentials, auth policy, logging policy, or write-operation controls.

## Acceptance Criteria Mapping

- Decide gateway stack: FastAPI.
- Create gateway container: `apps/openclaw-gateway`.
- Gateway network: only `media_net` for OPN-153.
- No raw passthrough routes: explicitly forbidden.
- `/health`: implemented unauthenticated.
- Jellyfin endpoint: `/v1/media/jellyfin/library` and `/v1/media/jellyfin/search`.
- Jellyseerr endpoint: `/v1/media/jellyseerr/search`.
- OpenClaw credential boundary: OpenClaw gets gateway URL and bearer token only.
- Media app keys: remain on the media host in `.env`.
- Gateway port restriction: documented host firewall allowlist.
- qBittorrent/NZBGet/Prowlarr: not exposed.
- README/runbook: required in `apps/openclaw-gateway/README.md`.
- Smoke test: required in `scripts/smoke-openclaw-gateway.sh`.
