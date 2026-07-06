# OPN-228 Ryot Gateway Design

## Linear Issue

OPN-228: Hook up selected Trakt replacement in OpenClaw

## Decision

OpenClaw should not receive `RYOT_BASE_URL` or `RYOT_ADMIN_ACCESS_TOKEN` directly for the durable Ryot integration. Add a narrow Ryot capability to `openclaw-gateway` and keep the Ryot admin token on the media host, alongside the other upstream service credentials already owned by the gateway runtime.

The OpenClaw runtime should continue to use only:

```text
MEDIA_GATEWAY_URL=http://<media-host-ip>:8088
MEDIA_GATEWAY_TOKEN=<gateway token stored outside Git>
```

Direct OpenClaw `RYOT_BASE_URL` / `RYOT_ADMIN_ACCESS_TOKEN` provisioning is a temporary bypass only and requires explicit approval.

## Goal

Unblock OPN-228 live Ryot verification by exposing a fixed, token-protected gateway probe endpoint that verifies Ryot GraphQL reachability without exposing raw Ryot credentials or arbitrary GraphQL execution to OpenClaw.

## Current State

Ryot was selected by OPN-227 and deployed by OPN-237. OPN-228 has an OpenClaw-side `ryot-probe` path, but it currently reports:

```text
Status: missing_config
Missing config: RYOT_BASE_URL, RYOT_ADMIN_ACCESS_TOKEN
```

No token values were read or printed and no services were touched during that probe.

The existing gateway already holds upstream credentials for Jellyfin, Jellyseerr, Sonarr, Radarr, and n8n. Its documented boundary is that OpenClaw calls fixed `/v1/...` endpoints with a gateway bearer token, while upstream service credentials stay on the media host.

## Architecture

Add Ryot as another upstream client inside `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/`. The client should call Ryot's GraphQL endpoint with the Ryot admin token, then normalize only the fields needed by OpenClaw.

Add a fixed gateway endpoint under `/v1/media/ryot/probe`. This endpoint must use the existing gateway bearer auth dependency and the existing upstream error mapping behavior. It must not expose raw `/backend/graphql`, arbitrary GraphQL queries, raw Ryot responses, headers, cookies, or token values.

Gateway runtime configuration gains:

```text
RYOT_URL=http://ryot:8000
RYOT_ADMIN_ACCESS_TOKEN=change-me
```

These values live in Komodo stack env or an untracked `apps/openclaw-gateway/.env`. `apps/openclaw-gateway/example.env` documents placeholders only.

## Endpoint Contract

### Health Probe

```text
GET /v1/media/ryot/probe
```

Response:

```json
{
  "status": "ok",
  "service": "ryot",
  "typename": "QueryRoot"
}
```

The gateway sends a fixed GraphQL query:

```graphql
query OpenClawRyotProbe {
  __typename
}
```

This endpoint exists to replace the direct OpenClaw `ryot-probe` environment check with a gateway-backed check.

### Media State Lookup Follow-Up

Media-state lookup is intentionally not exposed in this slice. Upstream Ryot v10 source exposes useful GraphQL fields such as `metadataSearch`, `metadataLookup`, `metadataDetails`, `userMetadataList`, and `userMetadataDetails`, but no single external-ID media-state field matching the originally proposed `openClawMediaState` shape exists. A future endpoint should be designed only after the exact lookup sequence and normalized response shape are verified against Ryot's real schema.

## Security Boundary

OpenClaw receives only the gateway URL and gateway token. Ryot admin credentials remain on the media host.

The gateway must not:

- expose a raw GraphQL passthrough route;
- accept caller-supplied GraphQL documents;
- log Ryot admin tokens, gateway bearer tokens, or full request headers;
- return raw Ryot payloads;
- mount Docker socket, host media paths, Ryot database files, or Ryot appdata;
- join extra Docker networks beyond those required for the existing gateway and Ryot service access.

The gateway may log route path, status code, latency, upstream service name, and upstream error class.

## Error Handling

Use the existing gateway behavior:

- Ryot timeouts map to `504` with a generic message such as `ryot timed out`.
- Ryot HTTP failures map to `502` with upstream status only.
- Ryot transport failures map to `502` with `ryot request failed`.
- Ryot GraphQL `errors` responses map to `502` with `ryot graphql error`, without returning raw error bodies that could include sensitive operational detail.

## Files Expected To Change

- `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/settings.py`
- `apps/openclaw-gateway/compose.yml`
- `apps/openclaw-gateway/example.env`
- `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/media.py`
- `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/ryot.py`
- `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/media.py`
- `apps/openclaw-gateway/openclaw-gateway/tests/test_settings.py`
- `apps/openclaw-gateway/openclaw-gateway/tests/test_ryot_client.py`
- `apps/openclaw-gateway/openclaw-gateway/tests/test_media_routes.py`
- `apps/openclaw-gateway/README.md`
- `scripts/smoke-openclaw-gateway.sh`

Nearby cleanup: `schemas/media.py` currently contains duplicated Jellyseerr and Jellyfin class definitions. If the implementer edits that file for Ryot schemas, remove the duplicate block in the same change to avoid expanding the duplication.

## Validation

Run non-deploying checks only:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest -q
```

```bash
docker compose --env-file apps/openclaw-gateway/example.env -f apps/openclaw-gateway/compose.yml config >/tmp/opn-228-openclaw-gateway-compose.yml
```

```bash
bash -n scripts/smoke-openclaw-gateway.sh
```

Live verification, if explicitly approved after implementation, should call the gateway endpoint with the gateway token and must not print token values.

## Deployment Checklist

Manual/UI work remains outside repo edits:

- Add `RYOT_URL` and `RYOT_ADMIN_ACCESS_TOKEN` to the openclaw-gateway Komodo stack environment.
- Redeploy the openclaw-gateway stack through Komodo.
- Confirm host firewall still limits the gateway port to the OpenClaw runtime IP.
- Update OpenClaw to call `/v1/media/ryot/probe` through `MEDIA_GATEWAY_URL` / `MEDIA_GATEWAY_TOKEN` instead of requiring direct Ryot env vars.
- Re-run the OPN-228 OpenClaw probe path and record the result in Linear without printing secrets.

## Self-Review

- Placeholder scan: no unfinished placeholder markers or unspecified secret values are present.
- Scope check: this spec covers only the gateway probe capability and docs needed to unblock OPN-228; OpenClaw-side client refactoring and Ryot media-state lookup are follow-ups after the gateway endpoint exists.
- Boundary check: the design preserves the existing OpenClaw gateway credential boundary and forbids raw Ryot GraphQL passthrough.
