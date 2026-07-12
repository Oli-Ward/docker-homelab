# OPN-264 Plane Gateway Adapter Design

> **Archived 2026-07-12:** This design spec is implemented and superseded by the current gateway/SDK split plus Linear OPN-275's REST adapter hardening scope. Keep this file as historical design context, not as the active Plane gateway spec.

## Scope

Build the first reusable Plane integration layer inside `apps/openclaw-gateway`. This slice does not replace Linear automation end-to-end yet. It creates the shared, tested API adapter that later Plane webhooks, ChatGPT/Codex tools, and OpenClaw write-back workflows can use.

## Context

Plane Commercial Edition is already installed and exposed privately at `https://plane.home.lab` through Nginx Proxy Manager. Plane uses its native login flow so desktop, mobile, and API/token flows are not blocked by forward-auth. The gateway is a FastAPI service with existing bearer-token authentication, typed upstream clients, Pydantic settings, and `respx` tests. It is the correct initial home for Plane access because it can keep Plane credentials on the media host and expose only narrow authenticated operations to OpenClaw.

Plane's API uses `X-API-Key` authentication. The relevant endpoints for this slice are:

- `GET /api/v1/workspaces/{workspace_slug}/work-items/search/`
- `GET /api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/`
- `POST /api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/`
- `GET /api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{resource_id}/`
- `PATCH /api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{resource_id}/`
- `POST /api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{resource_id}/comments/`
- project, state, and label list endpoints under the same workspace/project API.

## Design

Add a new `openclaw_gateway.clients.plane.PlaneClient` that owns Plane URL construction, `X-API-Key` authentication, pagination-friendly query parameters, and response normalization. The client should return Pydantic models rather than raw Plane payloads where practical, while keeping a `raw` field for fields that are not yet normalized.

Add a new protected router under `/v1/workflow/plane`. The route set is intentionally narrow:

- `GET /v1/workflow/plane/projects`
- `GET /v1/workflow/plane/projects/{project_id}/states`
- `GET /v1/workflow/plane/projects/{project_id}/labels`
- `GET /v1/workflow/plane/search?q=...&project_id=...&limit=...`
- `GET /v1/workflow/plane/projects/{project_id}/work-items`
- `GET /v1/workflow/plane/projects/{project_id}/work-items/{work_item_id}`
- `POST /v1/workflow/plane/projects/{project_id}/work-items`
- `PATCH /v1/workflow/plane/projects/{project_id}/work-items/{work_item_id}`
- `POST /v1/workflow/plane/projects/{project_id}/work-items/{work_item_id}/comments`

All routes use the existing gateway bearer token. The gateway must not expose the Plane API key or raw upstream error bodies. Write operations should accept only explicit JSON bodies for fields used by OpenClaw in the near term: `name`, `description_html`, `state_id`, `priority`, `label_ids`, `assignee_ids`, and `parent_id` for work items, plus `comment_html` for comments.

Configuration:

- `PLANE_API_BASE_URL`: defaults to `http://192.168.1.103:8085`.
- `PLANE_API_KEY`: required secret, stored in Komodo or untracked runtime env.
- `PLANE_WORKSPACE_SLUG`: required.
- `PLANE_DEFAULT_PROJECT_ID`: optional helper for later smoke commands.

## Security

Plane remains private behind `plane.home.lab`; the gateway talks to the API listener directly from the media host network path. Only authenticated OpenClaw gateway callers can use the new Plane routes. Plane token values stay outside Git and are never logged or returned in responses.

## Testing

Use TDD with `respx` for `PlaneClient` request shape and normalization. Add route tests with monkeypatched clients, matching the existing automation route tests. Verify settings validation rejects missing Plane token and workspace slug. Run the focused Plane tests and the full gateway test suite before handoff.

## Follow-Ups

After this adapter exists:

1. Create a real Plane API token and store it outside Git.
2. Run read-only smoke tests against the imported Plane workspace.
3. Replace Linear n8n pickup with Plane webhook verification and queueing.
4. Add OpenClaw write-back rules using this client.
5. Add ChatGPT/Codex integration against the same gateway layer.
