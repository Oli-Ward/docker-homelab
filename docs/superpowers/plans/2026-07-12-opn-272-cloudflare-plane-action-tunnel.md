# OPN-272 Cloudflare Plane Action Public Hostname Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the ChatGPT Plane Action through the existing remotely managed Cloudflare Tunnel hostname route, limited to approved Plane gateway routes.

**Architecture:** Reuse the installed `cloudflared.service` on `media-homelab`; it is a remotely managed tunnel connector, so route configuration belongs in the Cloudflare Zero Trust dashboard rather than a repo-managed `cloudflared` Docker stack or local `config.yml`. The dedicated hostname, for example `plane-api.<your-domain>`, should route only `/v1/workflow/plane/*` to the gateway's media-host origin. Gateway bearer authentication remains the application auth boundary; Cloudflare provides public TLS, DNS, route filtering, and rate limiting without interactive Cloudflare Access.

**Tech Stack:** systemd `cloudflared`, Cloudflare Zero Trust remotely managed tunnel routes, OpenAPI 3.1, gateway bearer auth.

---

## Issue Context

Linear issue: `OPN-272` - `Implement ChatGPT/Codex Plane Integration`

Approved ingress requirements:

- Dedicated public HTTPS hostname, for example `plane-api.<your-domain>`.
- No `.home.lab`, raw gateway host port, or origin IP exposure for ChatGPT Actions.
- Public tunnel ingress is restricted to `/v1/workflow/plane/*`.
- Gateway bearer authentication stays enabled.
- No Plane API key in ChatGPT, Cloudflare, or repo-managed tunnel config.
- No interactive Cloudflare Access login on the ChatGPT Action path.
- Cloudflare rate limiting and request filtering are required before desktop/phone smokes.

## File Structure

- Modify `apps/openclaw-gateway/chatgpt-actions/plane-openapi.yaml`
  - Replace the private `.home.lab` server URL with the public Action hostname placeholder.
- Modify `apps/openclaw-gateway/chatgpt-actions/README.md`
  - Replace the previous NPM/Auth/local-tunnel fallback with the approved remotely managed Cloudflare Tunnel path.
- Modify `README.md`
  - Document that the ChatGPT Action ingress is the deliberate public-hostname exception to the internal `.home.lab` pattern.

## Tasks

- [x] Verify the existing systemd `cloudflared` connector is active and has successful tunnel connections.
- [x] Verify the gateway origin reachable from media. Current live check: `http://192.168.1.103:8088/health` returns `200`; `http://127.0.0.1:8088/health` refuses because the gateway port is bound to the LAN IP.
- [ ] Configure the Cloudflare Zero Trust Public hostname route on the existing tunnel.
- [x] Update the Action OpenAPI server URL and setup docs.
- [x] Validate OpenAPI YAML parsing and confirm no `.home.lab` Action server remains.
- [x] Record remaining manual Cloudflare/Komodo/ChatGPT steps in Linear as `OPN-277`.

## Verification

Connector and origin checks:

```bash
systemctl status cloudflared --no-pager
journalctl -u cloudflared -n 100 --no-pager
docker ps --filter name=openclaw-gateway --format '{{.Names}}\t{{.Ports}}'
curl -sS -i --max-time 5 http://192.168.1.103:8088/health
```

Do not paste raw `systemctl status` output into tickets or docs because the
process arguments can include the connector token.

Repo checks:

```bash
python - <<'PY'
import yaml
with open("apps/openclaw-gateway/chatgpt-actions/plane-openapi.yaml", "r", encoding="utf-8") as fh:
    spec = yaml.safe_load(fh)
servers = [server["url"] for server in spec.get("servers", [])]
assert not any(".home.lab" in url for url in servers), servers
print("SERVERS", ",".join(servers))
PY
rg -n "plane-api.example.com|/v1/workflow/plane" apps/openclaw-gateway/chatgpt-actions README.md
git diff --check
```

Live checks after the Cloudflare Public hostname is configured:

```bash
curl -fsS -o /dev/null -w "%{http_code}\n" https://plane-api.<your-domain>/v1/workflow/plane/projects
curl -fsS -o /dev/null -w "%{http_code}\n" https://plane-api.<your-domain>/health
curl -fsS -H "Authorization: Bearer <gateway-token>" https://plane-api.<your-domain>/v1/workflow/plane/projects
```

Expected:

- Unauthenticated Plane-route request returns `401`.
- Unrelated gateway route returns `404` or Cloudflare block response.
- Authenticated read returns valid Plane data.
- No `.home.lab` hostname, raw gateway port, or Plane API key is exposed to ChatGPT.

## Self-Review

- Spec coverage: The plan covers dedicated public hostname, path restriction, bearer auth, no Access login, rate limiting checklist, OpenAPI update, smokes, and rollback.
- Placeholder scan: `plane-api.example.com`, `<your-domain>`, and `<gateway-token>` are explicit operator placeholders. No real secret values are present.
- Scope check: This is a single infrastructure slice; it does not change Plane, gateway route behavior, or ChatGPT account state directly.

## 2026-07-13 Update

`OPN-277` now tracks the remaining public gateway endpoint work. The current
repo state has an active `cloudflared` connector, healthy gateway origin at
`http://192.168.1.103:8088`, and a placeholder Action server URL of
`https://plane-api.example.com`. Do not import the Action as production until
the Cloudflare hostname is configured, verified, and substituted into
`plane-openapi.yaml`.
