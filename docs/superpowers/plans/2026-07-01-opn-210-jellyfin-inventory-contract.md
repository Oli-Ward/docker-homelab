# OPN-210 Jellyfin Inventory Contract

## Goal

Let OpenClaw retrieve a read-only Jellyfin inventory through the media gateway using only `MEDIA_GATEWAY_URL` and `MEDIA_GATEWAY_TOKEN`, with no direct Jellyfin credentials, Docker access, raw paths, or raw upstream passthrough.

## Constraints

- Keep the gateway route fixed at `GET /v1/media/jellyfin/library`.
- Preserve existing gateway auth and upstream secret boundary.
- Return normalized fields only.
- Document the full-response pagination mode and privacy boundary.
- Validate without deploying or restarting containers.

## Test Plan

1. Add Jellyfin client tests for normalized `library`, `runtime_minutes`, `genres`, and pagination metadata.
2. Add route tests proving the expanded response shape is serialized.
3. Add a client test proving raw Jellyfin path fields are not exposed.
4. Run focused tests red first, then implement.
5. Run the gateway test suite and compose config validation.

## Implementation Plan

1. Extend media response schemas with optional Jellyfin inventory metadata and a `pagination` object.
2. Update the Jellyfin client to request safe Jellyfin fields and normalize library name, runtime ticks, genres, and total count.
3. Keep Jellyseerr/search callers compatible with the shared media response schema.
4. Update `apps/openclaw-gateway/README.md` with the inventory contract, privacy boundary, and documented large-library behavior.
5. Commit the OPN-210 branch for review/merge.

## Verification

- `pytest tests/test_jellyfin_client.py tests/test_media_routes.py`
- `pytest -q`
- `docker compose --env-file apps/openclaw-gateway/example.env -f apps/openclaw-gateway/compose.yml config`
- `git diff --check`
