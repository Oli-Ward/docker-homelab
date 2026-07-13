# OPN-277 Public Gateway Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish and verify the dedicated public HTTPS endpoint used by the ChatGPT Plane Action.

**Architecture:** Reuse the already installed, remotely managed `cloudflared.service` on the media host. The Cloudflare Public Hostname route is configured in Cloudflare Zero Trust, points only the approved Action hostname/path at `http://192.168.1.103:8088`, and leaves gateway bearer authentication as the application boundary. The current public Action hostname is `https://plane-api.agentlobster.uk`; public TLS, route restriction, unauthenticated `401`, unrelated-path denial, authenticated read/write, and desktop/phone ChatGPT Action smokes have evidence. The exact Cloudflare control-plane rule export is not stored in this repo.

**Tech Stack:** systemd `cloudflared`, Cloudflare Zero Trust Public Hostnames, Cloudflare DNS/WAF/rate limiting, OpenAPI 3.1, `curl`, existing `openclaw-gateway`.

## Global Constraints

- Do not expose `.home.lab`, a raw gateway port, the origin IP, or the Plane API key to ChatGPT or public DNS.
- Do not use interactive Cloudflare Access on the server-to-server ChatGPT Action path.
- Do not read, print, or commit Cloudflare connector tokens, API tokens, gateway bearer tokens, Plane API keys, cookies, private keys, or `.env` files.
- Do not restart, redeploy, or mutate Docker/Komodo stacks for this ticket unless explicitly instructed.
- The current gateway origin is `http://192.168.1.103:8088`.
- The current Action hostname is `https://plane-api.agentlobster.uk`.
- Do not mark OPN-277 done or import the Action as production without authenticated read/write evidence and accepted Cloudflare filtering/rate-limit configuration.
- If the gateway bearer token is unavailable in the current shell, stop before authenticated smoke and record the blocker with evidence.

---

## File Structure

- Modify `apps/openclaw-gateway/chatgpt-actions/plane-openapi.yaml`
  - Keep the server URL on the verified public HTTPS hostname `https://plane-api.agentlobster.uk`.
- Modify `apps/openclaw-gateway/chatgpt-actions/README.md`
  - Record the verified hostname and public smoke commands without secrets.
- Modify `docs/superpowers/plans/2026-07-13-opn-277-public-gateway-endpoint.md`
  - Track which operational checks were completed and where the work stopped.

No Cloudflare tunnel config file should be added to this repo for this remotely managed connector.

### Task 1: Local Preflight

**Files:**
- Modify: `docs/superpowers/plans/2026-07-13-opn-277-public-gateway-endpoint.md`

**Interfaces:**
- Consumes: local `cloudflared.service`, local Docker read-only state, gateway health endpoint.
- Produces: evidence that the connector and gateway origin are ready for Cloudflare route work.

- [x] **Step 1: Verify cloudflared binary and service state**

Run:

```bash
command -v cloudflared
cloudflared --version
systemctl show cloudflared --property=LoadState,ActiveState,SubState --no-pager
```

Expected: binary path prints, version prints, and service shows `LoadState=loaded`, `ActiveState=active`, `SubState=running`.

- [x] **Step 2: Verify gateway origin without mutating Docker**

Run:

```bash
docker ps --filter name=openclaw-gateway --format '{{.Names}}\t{{.Ports}}'
curl -sS -i --max-time 5 http://192.168.1.103:8088/health | sed -n '1,12p'
```

Expected: `openclaw-gateway` shows `192.168.1.103:8088->8080/tcp`, and `/health` returns HTTP `200` with `{"status":"ok"}`.

- [x] **Step 3: Verify Cloudflare API capability without printing secrets**

Run:

```bash
if [ -n "${CLOUDFLARE_API_TOKEN:-}" ] || [ -n "${CF_API_TOKEN:-}" ]; then
  printf 'cloudflare_api_token_env=set\n'
else
  printf 'cloudflare_api_token_env=unset\n'
fi
```

Expected: if this prints `unset`, do not attempt Cloudflare API mutation from this shell.

### Task 2: Cloudflare Public Hostname Route

**Files:**
- Modify: `docs/superpowers/plans/2026-07-13-opn-277-public-gateway-endpoint.md`

**Interfaces:**
- Consumes: a concrete public hostname selected by the operator and Cloudflare Zero Trust access.
- Produces: a Cloudflare Public Hostname route from that hostname to `http://192.168.1.103:8088`.

- [x] **Step 1: Confirm a concrete hostname**

Use the hostname selected in Cloudflare Zero Trust. Recommended shape is a subdomain dedicated to this Action, such as `plane-api` under the owned public zone.

Selected hostname: `plane-api.agentlobster.uk`.

- [x] **Step 2: Configure the route in Cloudflare Zero Trust**

In Cloudflare Zero Trust:

```text
Networks -> Connectors -> Cloudflare Tunnels -> existing media tunnel -> Public Hostnames
```

Add a Public Hostname with:

```text
Hostname: plane-api.agentlobster.uk
Path: /v1/workflow/plane/*
Service: http://192.168.1.103:8088
```

Expected: Cloudflare creates DNS/routing for the hostname on the existing tunnel.

2026-07-13 evidence: `GET https://plane-api.agentlobster.uk/v1/workflow/plane/projects`
reached the gateway through Cloudflare and returned HTTP `401` with
`{"detail":"Missing bearer token"}`.

- [x] **Step 3: Add public filtering**

Configure Cloudflare rules for the Action hostname:

```text
Allow path: /v1/workflow/plane/*
Block unrelated paths
Allow methods needed by the Action: GET, POST, PATCH
Block other methods
Add rate limiting suitable for low-volume ChatGPT Action use
Do not enable interactive Access/challenge login
```

Expected: ChatGPT can make server-to-server API calls with bearer auth, while unrelated gateway routes are denied at Cloudflare.

2026-07-13 evidence: `GET https://plane-api.agentlobster.uk/health` returned
HTTP `403` from Cloudflare, so the unrelated gateway health route is not
publicly exposed. Rate limiting was accepted as Cloudflare dashboard
configuration; the exact control-plane rule export was not inspected or
committed from this shell.

### Task 3: Public Verification

**Files:**
- Modify: `docs/superpowers/plans/2026-07-13-opn-277-public-gateway-endpoint.md`

**Interfaces:**
- Consumes: configured public hostname and gateway bearer token from the operator secret store.
- Produces: public endpoint evidence safe to paste into Linear.

- [x] **Step 1: Verify local shell variables without printing secrets**

Use a shell where `PUBLIC_HOSTNAME` already contains the verified public
hostname and `GATEWAY_AUTH_TOKEN` already contains the gateway bearer token from
the operator secret store. Then run:

```bash
: "${PUBLIC_HOSTNAME:?set PUBLIC_HOSTNAME to the verified public hostname}"
: "${GATEWAY_AUTH_TOKEN:?set GATEWAY_AUTH_TOKEN from the operator secret store}"
```

Do not echo `GATEWAY_AUTH_TOKEN`.

Later authenticated smoke evidence was captured without printing the token or
payload.

- [x] **Step 2: Verify unauthenticated auth boundary**

Run:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" "https://${PUBLIC_HOSTNAME}/v1/workflow/plane/projects"
```

Expected: `401`.

2026-07-13T06:46:03Z result:

```text
HTTP/2 401
{"detail":"Missing bearer token"}
```

- [x] **Step 3: Verify unrelated-path denial**

Run:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" "https://${PUBLIC_HOSTNAME}/health"
```

Expected: `403`, `404`, or another Cloudflare block status that proves `/health` is not publicly exposed.

2026-07-13T06:46:03Z result:

```text
HTTP/2 403
server: cloudflare
```

- [x] **Step 4: Verify authenticated read**

Run:

```bash
curl -sS -H "Authorization: Bearer ${GATEWAY_AUTH_TOKEN}" "https://${PUBLIC_HOSTNAME}/v1/workflow/plane/projects"
```

Expected: JSON response with an `items` array and no Plane API key or raw upstream payload.

2026-07-13 Linear evidence records an authenticated public read returning HTTP
`200` with one project through `https://plane-api.agentlobster.uk`, without
printing the bearer token or raw payload.

### Task 4: Repo Hostname Update

**Files:**
- Modify: `apps/openclaw-gateway/chatgpt-actions/plane-openapi.yaml`
- Modify: `apps/openclaw-gateway/chatgpt-actions/README.md`
- Modify: `docs/superpowers/plans/2026-07-13-opn-277-public-gateway-endpoint.md`

**Interfaces:**
- Consumes: public verification from Task 3.
- Produces: Action OpenAPI document ready for ChatGPT import.

- [x] **Step 1: Replace the OpenAPI server URL**

In `apps/openclaw-gateway/chatgpt-actions/plane-openapi.yaml`, confirm:

```yaml
url: https://plane-api.agentlobster.uk
```

- [x] **Step 2: Update Action README**

In `apps/openclaw-gateway/chatgpt-actions/README.md`, record the verified
hostname and keep the secret-handling warnings.

- [x] **Step 3: Validate OpenAPI and docs**

Run:

```bash
python3 - <<'PY'
import yaml
path = 'apps/openclaw-gateway/chatgpt-actions/plane-openapi.yaml'
with open(path, 'r', encoding='utf-8') as fh:
    spec = yaml.safe_load(fh)
servers = [server['url'] for server in spec.get('servers', [])]
assert servers == ['https://plane-api.agentlobster.uk'], servers
assert not any(url.endswith('example.com') for url in servers), servers
assert not any('.home.lab' in url for url in servers), servers
assert 'state_id' not in spec['components']['schemas']['PlaneWorkItemCreate']['properties']
print('SERVERS', ','.join(servers))
print('PATHS', len(spec.get('paths', {})))
PY
! rg -n 'plane-api.example.com|\\.home\\.lab' apps/openclaw-gateway/chatgpt-actions
git diff --check
```

2026-07-13T06:46:43Z result: Python printed
`SERVERS https://plane-api.agentlobster.uk` and `PATHS 7`, `rg` found no
placeholder or `.home.lab` Action references, and `git diff --check` exited 0.

### Task 5: Linear Finish or Block Update

**Files:**
- No repo changes unless Task 4 completed.

**Interfaces:**
- Consumes: verification evidence and git status.
- Produces: accurate Linear state.

- [x] **Step 1: If Tasks 2-4 completed and authenticated read passes, mark OPN-277 Done**

Post a Linear comment with:

```text
Outcome: done
Hostname: record the verified hostname used in Task 3
Verification:
- unauthenticated Plane route: 401
- unrelated path: blocked
- authenticated read: passed
- OpenAPI server updated and parsed
Commit: include the commit hash if Task 4 changed repo files
Remaining follow-ups: ChatGPT Action import and desktop/phone smoke under OPN-272
```

- [x] **Step 2: Confirm the blocked path is no longer current**

Authenticated read/write evidence and desktop/phone Action smoke evidence were
recorded later on OPN-272 and OPN-277, so the earlier blocked path is no longer
current.

## Self-Review

- Spec coverage: The plan covers hostname/DNS, TLS, path restriction, bearer auth, no Plane key exposure, no interactive Access, filtering/rate limiting, external curl checks, OpenAPI update, rollback, and Linear status update. Authenticated read/write and desktop/phone smokes are evidenced in Linear; the Cloudflare rule export itself is not repo-managed.
- Placeholder scan: No public hostname placeholder remains in the Action files. `<gateway-token>` and `GATEWAY_AUTH_TOKEN` remain explicit runtime secret placeholders and must not be committed with real values.
- Scope check: This is an operational Cloudflare route task plus a small repo hostname substitution after live verification. It does not alter gateway route behavior, Plane data, Docker, Komodo, or ChatGPT account configuration.

## 2026-07-13 Pickup Attempt

Completed Task 1 from this session:

- `cloudflared` binary: `/usr/local/bin/cloudflared`
- `cloudflared` version: `2026.7.1`
- `cloudflared.service`: `LoadState=loaded`, `ActiveState=active`, `SubState=running`
- Docker read-only state: `openclaw-gateway` is published as `192.168.1.103:8088->8080/tcp`
- Gateway origin health: `http://192.168.1.103:8088/health` returned HTTP `200` with `{"status":"ok"}`
- Cloudflare API token env check: `CLOUDFLARE_API_TOKEN` and `CF_API_TOKEN` are unset in this shell

This pickup attempt originally stopped before Task 2 because the session did
not have a concrete public hostname or Cloudflare Zero Trust control-plane
access.

## 2026-07-13 Public Hostname Follow-up

Concrete hostname now known: `plane-api.agentlobster.uk`.

Evidence refreshed at 2026-07-13T06:46:03Z:

- `curl -sS -i --max-time 10 https://plane-api.agentlobster.uk/v1/workflow/plane/projects`
  returned HTTP `401` with `{"detail":"Missing bearer token"}`.
- `curl -sS -i --max-time 10 https://plane-api.agentlobster.uk/health`
  returned HTTP `403` from Cloudflare.
- `python3` OpenAPI parse confirmed server
  `https://plane-api.agentlobster.uk` and `7` paths.
- `rg -n 'plane-api.example.com|\.home\.lab' apps/openclaw-gateway/chatgpt-actions`
  found no matches.
- `git diff --check` passed.

## 2026-07-13 Final Smoke Evidence

Later tracker evidence resolved the public-ingress blockers:

- Authenticated public read returned HTTP `200` with one project and no token or
  raw payload printed.
- Desktop ChatGPT Action create reached the public hostname, passed gateway
  bearer authentication, and created Plane work item sequence `262`.
- Phone ChatGPT Action comment reached the public hostname and returned `200`.
- The follow-up default-state drift was fixed under OPN-272, redeployed through
  Komodo, and a fresh public create smoke produced a Plane item in `Todo`.

OPN-277 is closed in Linear as the public ingress dependency for OPN-272.
