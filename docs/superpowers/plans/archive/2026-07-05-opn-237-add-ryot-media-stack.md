# OPN-237 Add Ryot Media Stack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Ryot as the stateful media tracker on the media Docker host, with Postgres persistence, safe auth/proxy decisions, backup coverage, health verification, and chronological Linear updates.

**Architecture:** This must run in two phases. Phase 1 is report-only planning in the repo and Linear; Phase 2 requires explicit Oli approval before live inventory, Compose edits, Komodo deployment, appdata creation, Authentik/NPM/DNS/Homepage changes, Jellyfin integration, gateway/n8n runtime changes, or secret-store access. Ryot should live in the existing `apps/media` stack, use an internal Postgres service, join the existing `media_net` and `proxy_net` networks, store mutable database state under `${APPDATA_ROOT}/ryot-postgres`, and expose UI/API through the established NPM/Auth pattern rather than a direct public port.

**Tech Stack:** Docker Compose, Komodo, Ryot `ignisda/ryot:v10`, PostgreSQL 18 Alpine, TMDB access token, Authentik OIDC or proxy auth, Nginx Proxy Manager, AdGuard DNS, Homepage, Jellyfin webhook plugin, Linear.

---

## Approval Boundary

`OPN-237` is currently blocked on explicit live media Docker service-add approval. Until Oli approves the next step, only these actions are allowed:

- Read repo files and public documentation.
- Write this implementation plan.
- Comment in Linear with planning status.
- Run non-mutating local repo checks against the plan.

These actions remain approval-gated:

- Live media-host Docker, Komodo, appdata, storage, proxy, Authentik, DNS, Homepage, Jellyfin, n8n, gateway, secrets, firewall, or backup inspection.
- Compose edits in `apps/media/compose.yml` or `apps/media/example.env`.
- Deploy/redeploy/restart/pull/build/remove actions.
- Secret reads or printing real `.env` values.

## Current Evidence

- `apps/media/compose.yml` currently contains `jellyfin` and `jellyseerr`, both on `media_net` and `proxy_net`.
- `apps/media/example.env` defines `PUID`, `PGID`, `TZ`, `DATA_ROOT`, and `APPDATA_ROOT`; it has no Ryot variables yet.
- `README.md` documents the repo convention that user-facing services route through `*.home.lab`, NPM, and Authentik where appropriate.
- `OPN-227` selected Ryot as the canonical Trakt replacement.
- `OPN-236` expects the first real media Docker service-add run to update it chronologically.
- Ryot current docs show Docker Compose with Ryot plus Postgres; Postgres 15+ is required, the example uses `postgres:18-alpine`, Ryot uses `ignisda/ryot:v10`, and `/health` is available.
- Ryot configuration uses `DATABASE_URL`, `SERVER_ADMIN_ACCESS_TOKEN`, `FRONTEND_URL`, `TZ`, and `MOVIES_AND_SHOWS_TMDB_ACCESS_TOKEN` for movie/show tracking.
- Ryot OIDC needs `FRONTEND_URL`, `SERVER_OIDC_CLIENT_ID`, `SERVER_OIDC_CLIENT_SECRET`, `SERVER_OIDC_ISSUER_URL`, and an OIDC redirect URL of `<FRONTEND_URL>/api/auth`.
- Ryot IMDb import can import an exported watchlist CSV into the Watchlist collection.
- Ryot Jellyfin Sink requires the unofficial Jellyfin webhook plugin and uses a generated Ryot webhook URL; it works for media with valid TMDb IDs.

## Proposed Decisions

- **Stack placement:** add Ryot to `apps/media/compose.yml`, not a standalone stack.
- **Database:** add `ryot-db` Postgres service in the same stack.
- **Image versions:** use `ignisda/ryot:v10` and `postgres:18-alpine` initially. This avoids `latest` for a new stateful service while staying aligned with current Ryot major-version docs.
- **Networks:** attach `ryot` to `media_net` and `proxy_net`; attach `ryot-db` only to `media_net`.
- **Host port:** do not publish `8000:8000` by default. Let NPM reach `ryot:8000` on `proxy_net`.
- **State paths:** use `${APPDATA_ROOT}/ryot-postgres:/var/lib/postgresql` for the database. Do not create host directories until approval.
- **Secrets:** add placeholder names only to `apps/media/example.env`; real values stay in the untracked env/secret store.
- **Auth:** prefer Ryot OIDC with Authentik if approved, because Ryot supports it natively. Keep local auth enabled for initial bootstrap unless Oli explicitly chooses OIDC-only after account creation and backup.
- **Exposure:** prefer `https://ryot.home.lab` through NPM with the homelab certificate. Decide during approval whether it is LAN-only, Tailscale-only, or proxy-authenticated externally.
- **Homepage:** add a Homepage entry only after route and health verification.
- **Jellyfin Sink:** defer until Ryot is healthy and first user/auth is configured, then decide whether to configure the webhook plugin in this pass.
- **n8n/OpenClaw gateway:** no runtime integration in this ticket unless explicit approval expands scope; OPN-228 consumes the verified Ryot endpoint later.

### Task 1: Record Planning Checkpoint

**Files:**
- Create: `docs/superpowers/plans/2026-07-05-opn-237-add-ryot-media-stack.md`
- Update: Linear `OPN-237`
- Update: Linear `OPN-236`

- [ ] **Step 1: Verify no gated live actions have happened**

Run:

```bash
git status --short
rg -n "docker compose (up|down|pull|restart|rm|build)|docker (start|stop|restart|rm|rmi|pull|build|compose up|compose down)|komodo|authentik|nginx-proxy-manager|adguard" docs/superpowers/plans/2026-07-05-opn-237-add-ryot-media-stack.md
```

Expected: only documentation references to gated systems, no evidence of live mutation commands.

- [ ] **Step 2: Comment planning status in Linear**

Add this comment to `OPN-237`:

```markdown
Planning checkpoint for OPN-237.

Approval state: report-only workspace planning only. No live Docker/Komodo/appdata/proxy/Auth/DNS/Homepage/Jellyfin/n8n/gateway/secrets/storage/firewall inspection or mutation has been performed.

Plan saved: `docs/superpowers/plans/2026-07-05-opn-237-add-ryot-media-stack.md`

Current proposed shape:
- Add Ryot to `apps/media` rather than a standalone stack.
- Use Ryot plus Postgres.
- Use `${APPDATA_ROOT}/ryot-postgres` for database state after approval.
- Add only secret reference names/placeholders to repo files; never real values.
- Prefer NPM/Auth route `https://ryot.home.lab` instead of direct host-port exposure.
- Prefer Authentik OIDC if approved, with local auth kept for bootstrap unless explicitly changed after account/backup verification.
- Defer Jellyfin Sink and n8n/OpenClaw runtime hookups until Ryot is deployed and healthy unless Oli explicitly expands this ticket.

Next required action: Oli approval for the live service-add inventory/deployment step before any live inspection, Compose/env edits, appdata creation, proxy/Auth/DNS/Homepage changes, Jellyfin webhook work, or secret-store access.
```

Add this shorter comment to `OPN-236`:

```markdown
OPN-237 planning checkpoint recorded.

Plan: `docs/superpowers/plans/2026-07-05-opn-237-add-ryot-media-stack.md`

Approval state remains report-only. The first concrete service-add workflow run is still blocked on explicit approval for live inventory/deployment. No live host inspection or mutation has been performed in this checkpoint.
```

### Task 2: Approval-Gated Pre-Change Inventory

**Files:**
- Create: `diagnostics/build-lanes/2026-07-05-opn-237-ryot-service-add.md`
- Update: Linear `OPN-237`
- Update: Linear `OPN-236`

- [ ] **Step 1: Ask for explicit approval**

Ask Oli for approval using this exact scope:

```text
Please approve the OPN-237 live pre-change inventory step.

Scope requested: read-only Docker/Komodo/media appdata/proxy/Auth/DNS/Homepage/Jellyfin/gateway/n8n inventory sufficient to confirm current stack names, networks, routes, auth pattern, storage paths, backup coverage, and integration prerequisites.

Still excluded unless separately approved: deploy/redeploy/restart/pull/build/remove actions, appdata directory creation, Compose/env edits, NPM/Auth/DNS/Homepage mutations, Jellyfin plugin changes, n8n/gateway runtime changes, secret reads, and any destructive cleanup.
```

Do not continue Task 2 without the approval.

- [ ] **Step 2: Record approved inventory commands before running them**

Create `diagnostics/build-lanes/2026-07-05-opn-237-ryot-service-add.md`:

```markdown
# OPN-237 Ryot Service-Add Runbook

Date: 2026-07-05

## Approval Log

- Pre-change inventory approval: APPROVED by Oli at <record timestamp and channel>.
- Approved scope: read-only Docker/Komodo/media appdata/proxy/Auth/DNS/Homepage/Jellyfin/gateway/n8n inventory sufficient to confirm current stack names, networks, routes, auth pattern, storage paths, backup coverage, and integration prerequisites.
- Exclusions: no deploy/redeploy/restart/pull/build/remove, no appdata creation, no Compose/env edits, no NPM/Auth/DNS/Homepage mutation, no Jellyfin plugin changes, no n8n/gateway runtime changes, no secret reads, no destructive cleanup.

## Pre-Change Inventory Commands

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
docker network inspect media_net
docker network inspect proxy_net
docker inspect jellyfin jellyseerr nginx-proxy-manager authentik-server
docker logs --tail 120 nginx-proxy-manager
docker logs --tail 120 authentik-server
```

## Findings

Pending.

## Decisions

Pending.

## Implementation Log

Pending.

## Verification

Pending.

## Rollback/Disable Path

Pending.

## Follow-Ups

Pending.
```

- [ ] **Step 3: Run only approved read-only inventory**

Run the approved read-only commands and summarize outputs into the diagnostic file. Do not paste secrets, cookies, tokens, certificates, or raw env contents.

Expected findings to capture:

```text
Current media stack services and images
Current Docker network existence and attached services
Current proxy/Auth patterns for protected media apps
Current canonical local hostname decision candidates
Whether Jellyfin webhook plugin appears available or needs separate UI confirmation
Whether appdata and backup conventions cover new Ryot paths
Any repo/live drift found
```

### Task 3: Approval-Gated Repo Changes

**Files:**
- Modify: `apps/media/compose.yml`
- Modify: `apps/media/example.env`
- Modify: `README.md`
- Update: `diagnostics/build-lanes/2026-07-05-opn-237-ryot-service-add.md`

- [ ] **Step 1: Ask for explicit approval to edit repo Compose/env docs**

Ask:

```text
Please approve OPN-237 repo configuration edits.

Scope requested: edit `apps/media/compose.yml`, `apps/media/example.env`, `README.md`, and the OPN-237 diagnostic/runbook to add Ryot + Postgres configuration and deployment notes. No live deployment, appdata creation, secret reads, proxy/Auth/DNS/Homepage changes, or container restarts.
```

Do not edit these files without approval.

- [ ] **Step 2: Add Ryot services to Compose**

After approval, modify `apps/media/compose.yml` to add:

```yaml
  # Ryot - Media Tracker
  ryot:
    image: ignisda/ryot:v10
    container_name: ryot
    depends_on:
      - ryot-db
    networks:
      - media_net
      - proxy_net
    environment:
      - TZ=${TZ}
      - FRONTEND_URL=${RYOT_FRONTEND_URL}
      - DATABASE_URL=postgres://${RYOT_POSTGRES_USER}:${RYOT_POSTGRES_PASSWORD}@ryot-db:5432/${RYOT_POSTGRES_DB}
      - SERVER_ADMIN_ACCESS_TOKEN=${RYOT_SERVER_ADMIN_ACCESS_TOKEN}
      - MOVIES_AND_SHOWS_TMDB_ACCESS_TOKEN=${RYOT_TMDB_ACCESS_TOKEN}
      - DISABLE_TELEMETRY=${RYOT_DISABLE_TELEMETRY}
      - USERS_ALLOW_REGISTRATION=${RYOT_USERS_ALLOW_REGISTRATION}
      - SERVER_OIDC_CLIENT_ID=${RYOT_OIDC_CLIENT_ID}
      - SERVER_OIDC_CLIENT_SECRET=${RYOT_OIDC_CLIENT_SECRET}
      - SERVER_OIDC_ISSUER_URL=${RYOT_OIDC_ISSUER_URL}
      - FRONTEND_OIDC_BUTTON_LABEL=${RYOT_OIDC_BUTTON_LABEL}
    restart: unless-stopped

  # Ryot Postgres - Media Tracker Database
  ryot-db:
    image: postgres:18-alpine
    container_name: ryot-db
    networks:
      - media_net
    environment:
      - TZ=${TZ}
      - POSTGRES_DB=${RYOT_POSTGRES_DB}
      - POSTGRES_USER=${RYOT_POSTGRES_USER}
      - POSTGRES_PASSWORD=${RYOT_POSTGRES_PASSWORD}
    volumes:
      - ${APPDATA_ROOT}/ryot-postgres:/var/lib/postgresql
    restart: unless-stopped
```

Do not add a direct `ports:` mapping unless the approved exposure decision requires it.

- [ ] **Step 3: Add safe example env placeholders**

Add to `apps/media/example.env`:

```env
# Ryot media tracker
RYOT_FRONTEND_URL=https://ryot.home.lab
RYOT_POSTGRES_DB=ryot
RYOT_POSTGRES_USER=ryot
RYOT_POSTGRES_PASSWORD=change-me
RYOT_SERVER_ADMIN_ACCESS_TOKEN=change-me-long-random-token
RYOT_TMDB_ACCESS_TOKEN=your-tmdb-read-access-token
RYOT_DISABLE_TELEMETRY=true
RYOT_USERS_ALLOW_REGISTRATION=false
RYOT_OIDC_CLIENT_ID=ryot
RYOT_OIDC_CLIENT_SECRET=change-me
RYOT_OIDC_ISSUER_URL=https://auth.home.lab/application/o/ryot/
RYOT_OIDC_BUTTON_LABEL=Continue with Authentik
```

- [ ] **Step 4: Update README service inventory**

Add `Ryot - Media tracker` under `### Media`, and add `ryot.home.lab` to domain examples if route approval selected that hostname.

- [ ] **Step 5: Check for accidental secrets**

Run:

```bash
rg -n "password|token|secret|api[_-]?key|cookie|authorization|privkey|BEGIN " apps/media/compose.yml apps/media/example.env README.md diagnostics/build-lanes/2026-07-05-opn-237-ryot-service-add.md
```

Expected: only placeholder values and generic variable names.

### Task 4: Validate Repo Configuration Before Deployment

**Files:**
- Check: `apps/media/compose.yml`
- Check: `apps/media/example.env`
- Update: `diagnostics/build-lanes/2026-07-05-opn-237-ryot-service-add.md`

- [ ] **Step 1: Validate Compose with example env**

Run:

```bash
docker compose --env-file apps/media/example.env -f apps/media/compose.yml config
```

Expected: exit 0, rendered services include `ryot` and `ryot-db`, no secret values beyond placeholders.

- [ ] **Step 2: Validate variable coverage**

Run:

```bash
python3 - <<'PY'
import pathlib, re
compose = pathlib.Path("apps/media/compose.yml").read_text()
example = pathlib.Path("apps/media/example.env").read_text()
vars_in_compose = sorted(set(re.findall(r"\$\{([A-Z0-9_]+)\}", compose)))
vars_in_example = {
    line.split("=", 1)[0]
    for line in example.splitlines()
    if line and not line.startswith("#") and "=" in line
}
missing = [name for name in vars_in_compose if name not in vars_in_example]
if missing:
    print("Missing example env variables:", ", ".join(missing))
    raise SystemExit(1)
print("All compose variables are present in apps/media/example.env")
PY
```

Expected: exit 0.

### Task 5: Approval-Gated Deployment Preparation

**Files:**
- Update: `diagnostics/build-lanes/2026-07-05-opn-237-ryot-service-add.md`
- Update: Linear `OPN-237`
- Update: Linear `OPN-236`

- [ ] **Step 1: Ask for explicit deployment preparation approval**

Ask:

```text
Please approve OPN-237 deployment preparation.

Scope requested: create required appdata directory/check ownership if needed, add real secret values to the approved untracked env/secret store by name, and prepare Komodo deployment inputs for the media stack.

Still excluded unless separately approved: actual deploy/redeploy/restart/pull/build/remove actions, proxy/Auth/DNS/Homepage mutations, Jellyfin plugin changes, n8n/gateway runtime changes, and printing or copying secret values.
```

- [ ] **Step 2: Record secret reference names only**

Record these names in the diagnostic file, with no values:

```text
RYOT_POSTGRES_PASSWORD
RYOT_SERVER_ADMIN_ACCESS_TOKEN
RYOT_TMDB_ACCESS_TOKEN
RYOT_OIDC_CLIENT_SECRET
```

- [ ] **Step 3: Confirm backup/checkpoint readiness**

Before any stateful deployment, record that Oli has confirmed backups or checkpoints for:

```text
media Docker Compose repo
${APPDATA_ROOT}
Nginx Proxy Manager config
Authentik/Postgres state
AdGuard config
Komodo state
Jellyfin config if Jellyfin Sink will be touched
```

Do not proceed to deployment if backup readiness is unknown.

### Task 6: Approval-Gated Komodo Deployment

**Files:**
- Update: `diagnostics/build-lanes/2026-07-05-opn-237-ryot-service-add.md`
- Update: Linear `OPN-237`
- Update: Linear `OPN-236`

- [ ] **Step 1: Ask for explicit deploy approval**

Ask:

```text
Please approve OPN-237 Komodo deployment of the media stack with Ryot.

Scope requested: deploy the repo-managed media stack change through Komodo and run read-only post-deploy verification. This may create/start Ryot and Ryot Postgres containers and initialize `${APPDATA_ROOT}/ryot-postgres`.

Still excluded unless separately approved: unrelated stack changes, direct `docker compose up/down/pull`, destructive cleanup, proxy/Auth/DNS/Homepage mutations, Jellyfin plugin changes, and n8n/gateway runtime changes.
```

- [ ] **Step 2: Deploy through Komodo only**

Use Komodo as the source of truth for deployment. Do not run `docker compose up`, `docker compose down`, `docker compose pull`, or restart containers directly.

- [ ] **Step 3: Verify containers and health**

Run read-only verification after Komodo deploy:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' | rg 'ryot|NAMES'
docker logs --tail 120 ryot
docker logs --tail 120 ryot-db
curl -fsS --max-time 10 http://ryot:8000/health
```

If `curl http://ryot:8000/health` is not resolvable from the host, run an approved read-only equivalent from an existing container on `proxy_net` or `media_net`.

Expected: `ryot` and `ryot-db` are running, Ryot logs show successful database migration/startup, and `/health` returns success.

### Task 7: Approval-Gated Auth, Proxy, DNS, Homepage, And Integration Work

**Files:**
- Modify if approved after route verification: `apps/utilities/homepage/services.yaml`
- Update: `diagnostics/build-lanes/2026-07-05-opn-237-ryot-service-add.md`
- Update: Linear `OPN-237`
- Update: Linear `OPN-228`
- Update: Linear `OPN-236`

- [ ] **Step 1: Ask for explicit external config approval**

Ask:

```text
Please approve OPN-237 external route/auth/dashboard configuration.

Scope requested: configure NPM route, Authentik OIDC or proxy auth, AdGuard DNS record if needed, Homepage entry after verification, and optional Jellyfin Sink setup decision.

Still excluded unless separately approved: n8n/OpenClaw runtime hookup, broad Jellyfin admin changes outside webhook setup, unrelated route/auth changes, and secret value disclosure.
```

- [ ] **Step 2: Configure NPM and DNS for selected exposure**

If `ryot.home.lab` is selected:

```text
NPM host: ryot.home.lab
Scheme: http
Forward hostname: ryot
Forward port: 8000
Websockets: enabled if NPM template normally enables it
SSL: homelab certificate
Force SSL: enabled
DNS: AdGuard rewrite/record for ryot.home.lab if not covered by wildcard
```

- [ ] **Step 3: Configure Authentik OIDC if selected**

Use these Ryot-side values:

```text
FRONTEND_URL=https://ryot.home.lab
SERVER_OIDC_CLIENT_ID=<secret-store reference only>
SERVER_OIDC_CLIENT_SECRET=<secret-store reference only>
SERVER_OIDC_ISSUER_URL=<Authentik provider issuer URL>
FRONTEND_OIDC_BUTTON_LABEL=Continue with Authentik
```

Authentik redirect URL:

```text
https://ryot.home.lab/api/auth
```

Keep local auth enabled for bootstrap unless Oli explicitly approves `USERS_DISABLE_LOCAL_AUTH=true` after account/backup verification.

- [ ] **Step 4: Verify UI reachability and auth**

Run:

```bash
curl -k -sS -I --max-time 10 https://ryot.home.lab | sed -n '1,20p'
curl -k -fsS --max-time 10 https://ryot.home.lab/health
```

Expected: route reaches Ryot through NPM, TLS is valid for the homelab path, and auth behavior matches the selected OIDC/proxy-auth decision.

- [ ] **Step 5: Add Homepage entry after route verification**

Only after route verification, add Ryot to `apps/utilities/homepage/services.yaml` following existing local style. Do not add widget API secrets unless a safe supported widget path exists and is approved.

- [ ] **Step 6: Decide Jellyfin Sink**

If approved in this pass, configure Ryot Jellyfin Sink:

```text
Generate Ryot Jellyfin Sink webhook URL in Ryot integration settings.
In Jellyfin webhook plugin, add webhook URL with Payload format "Default".
Events: Play, Pause, Resume, Stop, Progress.
User filter: Oli's selected Jellyfin user.
Requirement: media must have valid TMDb IDs.
```

Record whether this was configured or deferred.

### Task 8: Final Verification, Rollback, And Linear Updates

**Files:**
- Check: `apps/media/compose.yml`
- Check: `apps/media/example.env`
- Check: `README.md`
- Check if modified: `apps/utilities/homepage/services.yaml`
- Update: `diagnostics/build-lanes/2026-07-05-opn-237-ryot-service-add.md`
- Update: Linear `OPN-237`
- Update: Linear `OPN-228`
- Update: Linear `OPN-236`

- [ ] **Step 1: Run final repo checks**

Run:

```bash
docker compose --env-file apps/media/example.env -f apps/media/compose.yml config
git diff --check
git status --short
```

Expected: Compose renders, no whitespace errors, changed files are only the approved repo files plus diagnostics/plans.

- [ ] **Step 2: Run final live read-only checks**

Run approved read-only checks:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' | rg 'ryot|NAMES'
docker logs --tail 120 ryot
docker logs --tail 120 ryot-db
curl -k -fsS --max-time 10 https://ryot.home.lab/health
```

Expected: Ryot and Postgres are running and health endpoint succeeds through the selected route.

- [ ] **Step 3: Document rollback/disable path**

Record:

```text
Rollback through Komodo to previous media stack revision.
Disable or remove NPM `ryot.home.lab` host.
Disable or remove Authentik Ryot application/provider/outpost entry.
Remove AdGuard `ryot.home.lab` record if it was added.
Remove Homepage Ryot entry if it was added.
Preserve `${APPDATA_ROOT}/ryot-postgres` until Oli confirms backup/export and deletion intent.
Do not delete Ryot database state as part of routine rollback.
```

- [ ] **Step 4: Update dependent Linear tickets**

Final `OPN-237` comment:

```markdown
Outcome: <done or blocked>.

What changed:
- <repo files changed>
- <live services touched through approved steps>
- <auth/proxy/DNS/Homepage decisions>
- <Jellyfin Sink decision>
- <n8n/OpenClaw gateway decision>

Verification:
- `<command>` -> <result>
- `<command>` -> <result>

Secrets:
- Secret references recorded by name only. No secret values stored in Git, Linear, diagnostics, or memory.

Rollback:
- <recorded rollback path>

Commit/branch/PR:
- <hash/branch/PR or none>

Remaining follow-ups:
- <None or exact follow-up tickets>
```

Update `OPN-228`:

```markdown
Ryot service status for OpenClaw hookup:
- URL/route: <verified route or blocked>
- Auth mode: <OIDC/proxy/local/bootstrap>
- Health verification: <command/result>
- API/connectivity notes: <safe non-secret notes>
- Remaining connector work: <exact next action>
```

Update `OPN-236` with chronological workflow evidence:

```markdown
OPN-237 service-add workflow run update:
- Approvals: <list>
- Commands: <safe command list>
- Expected/actual results: <summary>
- Services touched: <list>
- Verification: <summary>
- Rollback: <summary>
- Workflow follow-ups: <changes needed to reusable process or None>
```

- [ ] **Step 5: Move Linear status only after verification**

If all acceptance criteria are met and verification passed, move `OPN-237` to Done. If approval is missing or deployment/health is blocked, keep it Blocked or active with the exact blocker in a comment.

## Sources Checked

- Ryot installation docs: https://docs.ryot.io/
- Ryot configuration docs: https://docs.ryot.io/configuration
- Ryot deployment docs: https://docs.ryot.io/deployment
- Ryot authentication docs: https://docs.ryot.io/guides/authentication
- Ryot IMDb import docs: https://docs.ryot.io/importing/imdb
- Ryot Jellyfin Sink docs: https://docs.ryot.io/integrations/jellyfin-sink
- OPN-227 investigation: `diagnostics/build-lanes/2026-07-04-opn-227-trakt-replacement.md`

## Self-Review

- Spec coverage: The plan covers pre-change inventory, Ryot + Postgres shape, appdata/database path, env/secret references, TMDB token requirement, Authentik/OIDC, proxy/DNS/Homepage, backup/readback, health verification, rollback, Jellyfin Sink, n8n/OpenClaw scope, OPN-236 updates, and OPN-228 unblock/update.
- Placeholder scan: No placeholder implementation steps use `TBD` or `TODO`; angle-bracket values appear only where runtime evidence must be recorded after approval.
- Type/config consistency: Ryot env variable names match current Ryot docs; Compose variable placeholders are paired with planned `apps/media/example.env` entries.
