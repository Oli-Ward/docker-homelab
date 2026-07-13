# ChatGPT Plane Action

This directory contains the ChatGPT Action contract for OPN-272. It calls the
existing `openclaw-gateway` Plane routes through the dedicated Cloudflare Tunnel
Action hostname and uses the gateway bearer token. Do not give ChatGPT the Plane
API key.

OPN-277 tracks the remaining public hostname work. Do not import this Action as
production while `plane-openapi.yaml` still uses `https://plane-api.example.com`.

The Action follows the current OpenAI GPT Actions model: import an OpenAPI
schema, then configure Action authentication in the GPT editor as API Key bearer
auth. Use the gateway bearer token from the gateway runtime secret store.

## Files

- `plane-openapi.yaml` is the ChatGPT Action OpenAPI contract.
- The same operation set is available locally through `openclaw-plane-tool`.

## Setup

1. Redeploy `openclaw-gateway` through Komodo after the adapter and CLI changes
   land.
2. Confirm the existing systemd `cloudflared` connector is active on
   `media-homelab`. Do not run `cloudflared tunnel login` or create a local
   tunnel `config.yml` for this remotely managed connector. Avoid sharing raw
   `systemctl status` output because the process arguments can include the
   connector token.
3. In Cloudflare Zero Trust, open the existing tunnel under
   **Networks -> Connectors -> Cloudflare Tunnels**.
4. Add a Published application / Public hostname, for example
   `plane-api.<your-domain>`.
5. Point the service to the gateway's host-reachable origin on media. The
   current gateway binding verified from Docker is:

   ```text
   http://192.168.1.103:8088
   ```

   `http://127.0.0.1:8088` is not valid for the current binding because the
   gateway port is bound to the media host LAN IP.
6. Restrict Cloudflare routing and rules to `/v1/workflow/plane/*`.
7. Add Cloudflare rate limiting and safe request filtering for the Action
   hostname. Do not use interactive Cloudflare Access on this path.
8. Replace the placeholder `https://plane-api.example.com` server URL in
   `plane-openapi.yaml` with the real public hostname.
9. Verify unauthenticated public requests to an allowed Plane route return
   `401`, unrelated paths are denied, and an authenticated read succeeds.
10. Import `plane-openapi.yaml` into the GPT Action builder.
11. Configure Action authentication with the gateway bearer token stored outside
   Git.
12. Keep the Plane API key only in the gateway runtime environment.

Do not paste real `GATEWAY_AUTH_TOKEN`, `PLANE_API_KEY`, cookies, session
tokens, or private keys into this repo.

## Tool Boundary

Allowed operations:

- List projects, states, and labels.
- Search, list, and read work items.
- Create one work item in an explicit project.
- Update one explicit work item.
- Comment on one explicit work item.

Out of scope:

- Delete, archive, restore, or bulk update operations.
- Raw Plane API passthrough.
- Docker, Komodo, n8n admin, or host access.
- Direct Plane API keys in ChatGPT or Codex.

ChatGPT create requests do not expose a create-time `state_id`. The gateway and
local Codex adapter resolve omitted create state to `Todo`, and the local
adapter rejects create requests that try to enter `Ready for Agent`.

## Read-First Smoke

1. Run `listPlaneProjects`.
2. Run `listPlaneStates` for the intended Openclaw project.
3. Confirm the `Todo` state ID.
4. Run `searchPlaneWorkItems` for `OPN-272`.

Stop if any read operation fails.

Before running ChatGPT smokes, verify the public ingress:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://plane-api.<your-domain>/v1/workflow/plane/projects
curl -sS -o /dev/null -w "%{http_code}\n" https://plane-api.<your-domain>/health
curl -sS -H "Authorization: Bearer <gateway-token>" https://plane-api.<your-domain>/v1/workflow/plane/projects
```

Expected:

- Allowed route without bearer token returns `401`.
- Unrelated route returns `404` or a Cloudflare block response.
- Allowed route with bearer token returns Plane project data.

## Write Smoke

Create exactly one marked smoke ticket:

```text
[SMOKE][OPN-272] ChatGPT Plane action create smoke
```

Expected behavior:

- The ticket is created in the intended Openclaw project.
- The ticket starts in `Todo`.
- A follow-up comment can be added to the same ticket.
- A narrow update can be made to the same ticket.
- No delete, archive, or bulk operation exists.
- Gateway logs include the create/comment/update audit records.

## Phone Validation

From the ChatGPT phone app, ask to create the same marked smoke ticket in the
intended project. Confirm it lands in `Todo` and can be searched/read afterward.

## Rollback

Disable or remove the ChatGPT Action registration. Plane itself and the gateway
routes do not need to be rolled back for Action-only failures.

For public ingress rollback, remove or disable the Cloudflare DNS route and
tunnel route for the Action hostname. Leave Plane and the internal gateway
running.
