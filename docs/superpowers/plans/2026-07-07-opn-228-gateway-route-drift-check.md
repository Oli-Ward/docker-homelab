# OPN-228 Gateway Route Drift Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Determine whether OPN-228 can resume or remains blocked after the latest live gateway verification returned HTTP 404 for `/v1/media/ryot/probe`.

**Architecture:** Treat `/home/oli/docker` as the media Docker source configuration and the live Docker state as diagnostic evidence only. Do not deploy, restart, pull, rebuild, or mutate containers; Komodo remains the deployment path. Record repo-vs-live drift and update Linear with a narrow next action.

**Tech Stack:** Docker Compose source files, FastAPI OpenClaw gateway, Ryot, curl, Docker read-only inspection, Linear.

## Global Constraints

- Do not run `docker compose up`, `docker compose down`, `docker compose pull`, or restart containers directly.
- Do not read, print, store, or infer real secret values.
- Do not mutate live Docker state; use read-only checks only.
- Keep OpenClaw on `MEDIA_GATEWAY_URL` and `MEDIA_GATEWAY_TOKEN`; keep `RYOT_ADMIN_ACCESS_TOKEN` in the gateway runtime only.
- Any deploy/redeploy must be done through Komodo after review.

---

### Task 1: Confirm Local Source And Live Route Drift

**Files:**
- Read: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/media.py`
- Read: `apps/openclaw-gateway/compose.yml`
- Read: `scripts/smoke-openclaw-gateway.sh`
- Modify: `docs/superpowers/plans/2026-07-07-opn-228-gateway-route-drift-check.md`

**Interfaces:**
- Consumes: Linear comments showing the OpenClaw `ryot-probe` reached `http://192.168.1.103:8088/v1/media/ryot/probe` and received HTTP 404.
- Produces: A Linear-ready drift finding and next action.

- [x] **Step 1: Inspect Linear state**

Run:

```bash
# Via Linear MCP
get_issue OPN-228
list_comments OPN-228
```

Expected: issue is `Blocked`; latest blocker is live media gateway route returning HTTP 404 while `/health` returns HTTP 200.

Actual: OPN-228 was `Blocked`; latest comment reported `ryot-probe` reached `http://192.168.1.103:8088/v1/media/ryot/probe` and returned HTTP 404 while gateway `/health` returned HTTP 200.

- [x] **Step 2: Inspect local source**

Run:

```bash
rg -n "ryot/probe|RYOT_URL|RYOT_ADMIN_ACCESS_TOKEN|MEDIA_GATEWAY_URL|MEDIA_GATEWAY_TOKEN|probe" apps/openclaw-gateway scripts docs diagnostics README.md
```

Expected: local source contains `GET /v1/media/ryot/probe`, gateway compose env for `RYOT_URL` and `RYOT_ADMIN_ACCESS_TOKEN`, docs, tests, and smoke coverage.

Actual: local source contains the route in `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/media.py`, compose env in `apps/openclaw-gateway/compose.yml`, docs in `apps/openclaw-gateway/README.md`, and smoke coverage in `scripts/smoke-openclaw-gateway.sh`.

- [x] **Step 3: Check repo state**

Run:

```bash
git status --short --branch
git log --oneline --decorate -n 20
```

Expected: identify whether the gateway code is committed locally and whether unrelated dirty files exist.

Actual: branch is `main...origin/main [ahead 10]`; HEAD is `2af6aac OPN-228: add Ryot gateway probe`. Untracked files exist for OPN-239 and OPN-234 and are unrelated to this pickup.

- [x] **Step 4: Run read-only live checks**

Run:

```bash
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' | rg 'openclaw-gateway|ryot|nginx|authentik|jellyfin|jellyseerr'
curl -sS -o /dev/null -w 'health=%{http_code}\n' http://192.168.1.103:8088/health
curl -sS -o /dev/null -w 'ryot_probe_noauth=%{http_code}\n' http://192.168.1.103:8088/v1/media/ryot/probe
```

Expected: gateway and Ryot containers are running; health returns 200; unauthenticated route check should return an auth error if the route exists, or 404 if the live container lacks the route.

Initial actual:

```text
openclaw-gateway  openclaw-gateway-openclaw-gateway  Up 24 hours  192.168.1.103:8088->8080/tcp
ryot              ignisda/ryot:v10                   Up 22 hours
ryot-db           postgres:18-alpine                 Up 24 hours
health=200
ryot_probe_noauth=404
```

Recheck actual after focused local validation:

```text
health=200
ryot_probe_noauth=401
```

Interpretation: the live gateway route is now present and protected by bearer auth. The earlier 404 route blocker is cleared, but this session does not have the authenticated OpenClaw runtime probe requirements locally.

- [x] **Step 5: Validate local source still passes focused checks**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
pytest -q tests/test_media_routes.py::test_ryot_probe_route_requires_auth tests/test_media_routes.py::test_ryot_probe_route_returns_normalized_status tests/test_ryot_client.py
cd /home/oli/docker
docker compose --env-file apps/openclaw-gateway/example.env -f apps/openclaw-gateway/compose.yml config >/tmp/opn-228-openclaw-gateway-compose.yml
bash -n scripts/smoke-openclaw-gateway.sh
git diff --check -- docs/superpowers/plans/2026-07-07-opn-228-gateway-route-drift-check.md apps/openclaw-gateway
```

Expected: focused gateway tests pass, compose renders with example env, smoke script syntax is valid, and diff check exits 0.

Actual:

```text
pytest focused gateway checks: 5 passed, 137 warnings
docker compose config with apps/openclaw-gateway/example.env: exit 0
bash -n scripts/smoke-openclaw-gateway.sh: exit 0
git diff --check: exit 0
```

- [x] **Step 6: Update Linear**

Use Linear MCP to move OPN-228 to `Blocked` if it is not already blocked, then add a comment with:

- Outcome: blocked.
- Evidence: local source has `/v1/media/ryot/probe`; live gateway health is 200; live `/v1/media/ryot/probe` moved from 404 to 401 before auth during this pickup.
- Interpretation: the route is now deployed and auth-protected, but authenticated OpenClaw probe verification cannot run from this local shell because `MEDIA_GATEWAY_URL`, `MEDIA_GATEWAY_TOKEN`, and `GATEWAY_AUTH_TOKEN` are absent and `/home/openclaw/.openclaw/workspace` is not present.
- Verification commands and results.
- Remaining follow-ups: run the authenticated OpenClaw `ryot-probe` command from the OpenClaw runtime or a shell with `MEDIA_GATEWAY_URL` / `MEDIA_GATEWAY_TOKEN` injected without printing secrets.

Actual: Linear was moved to `In Progress` for this pickup, then back to `Blocked`. Final blocked update posted in Linear comment `17cd4359-d90e-4b1a-bc4f-df5ba4120432`.
