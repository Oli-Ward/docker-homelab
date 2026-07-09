# OPN-250 Ryot Auth Env Drift Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore Ryot login access by removing the stale live `USERS_DISABLE_LOCAL_AUTH=true` override and redeploying the Komodo-managed media stack so Ryot uses the repo default `RYOT_USERS_DISABLE_LOCAL_AUTH=false`.

**Architecture:** Ryot is defined in `apps/media/compose.yml` and is deployed by Komodo from the media stack source. The durable compose source already renders `USERS_DISABLE_LOCAL_AUTH=false` when `RYOT_USERS_DISABLE_LOCAL_AUTH` is omitted or set to `false`; the fix is to correct the Komodo/live stack environment and redeploy, not to mutate Docker containers directly.

**Tech Stack:** Docker Compose, Komodo, Ryot `ignisda/ryot:v10`, PostgreSQL `postgres:18-alpine`, Authentik OIDC.

## Global Constraints

- Komodo is the source of truth for deploying, restarting, updating, and stopping stacks.
- Do not run `docker compose up`, `docker compose down`, `docker compose pull`, or restart containers directly unless explicitly asked.
- Do not print, copy, normalize, or infer real secret values.
- Validate compose changes with non-deploying checks only.
- Treat live Docker state as diagnostic evidence, not the place to make durable changes.
- Before stateful or storage-affecting changes, confirm backups/checkpoints exist; this plan only changes environment and redeploys the existing stack.

---

### Task 1: Confirm Source And Live Drift

**Files:**
- Read: `apps/media/compose.yml`
- Read: `apps/media/example.env`
- Read only the `RYOT_USERS_DISABLE_LOCAL_AUTH` key from ignored `apps/media/.env` if present.

**Interfaces:**
- Consumes: OPN-250 issue body.
- Produces: Root-cause evidence showing source config and live container disagree.

- [ ] **Step 1: Verify the repo default is local-auth enabled**

Run:

```bash
docker compose --env-file apps/media/example.env -f apps/media/compose.yml config --format json | jq -r '.services.ryot.environment.USERS_DISABLE_LOCAL_AUTH'
```

Expected: `false`

- [ ] **Step 2: Verify the live container still has the stale value without printing secrets**

Run:

```bash
docker inspect ryot --format '{{range .Config.Env}}{{println .}}{{end}}' | rg '^USERS_DISABLE_LOCAL_AUTH='
```

Expected before fix: `USERS_DISABLE_LOCAL_AUTH=true`

- [ ] **Step 3: Check whether the ignored local media env has the key**

Run:

```bash
sh -lc 'if [ -f apps/media/.env ]; then rg -n "^RYOT_USERS_DISABLE_LOCAL_AUTH=" apps/media/.env || printf "RYOT_USERS_DISABLE_LOCAL_AUTH not set in apps/media/.env\n"; else printf "apps/media/.env missing\n"; fi'
```

Expected in the current observed state: `RYOT_USERS_DISABLE_LOCAL_AUTH not set in apps/media/.env`

### Task 2: Correct The Komodo Media Stack Environment

**Files:**
- No repo files should change for this task unless investigation finds the source compose/example env no longer matches the expected value.

**Interfaces:**
- Consumes: Task 1 evidence.
- Produces: Komodo media stack environment with no stale `USERS_DISABLE_LOCAL_AUTH=true` override.

- [ ] **Step 1: Open the Komodo media stack environment**

In Komodo, inspect the media stack configuration and environment variables for Ryot.

Expected: find either `USERS_DISABLE_LOCAL_AUTH=true` or `RYOT_USERS_DISABLE_LOCAL_AUTH=true` in the media stack env/override surface.

- [ ] **Step 2: Remove or correct the stale override**

Set the durable environment so Ryot resolves to local auth enabled:

```env
RYOT_USERS_DISABLE_LOCAL_AUTH=false
```

Do not change Ryot OIDC client secret, admin access token, database password, or TMDB token values as part of this task.

- [ ] **Step 3: Redeploy through Komodo**

Use Komodo to redeploy the media stack. Do not run direct `docker compose up`, restart, pull, or recreate commands outside Komodo.

Expected: Komodo recreates the Ryot container from the same repo compose file with updated environment.

### Task 3: Verify Ryot Auth Is Restored

**Files:**
- No repo files should change.

**Interfaces:**
- Consumes: Redeployed media stack from Task 2.
- Produces: Verification evidence for OPN-250 final update.

- [ ] **Step 1: Verify the live Ryot environment**

Run:

```bash
docker inspect ryot --format '{{range .Config.Env}}{{println .}}{{end}}' | rg '^(USERS_DISABLE_LOCAL_AUTH|SERVER_OIDC_ISSUER_URL|FRONTEND_OIDC_BUTTON_LABEL)='
```

Expected after fix: `USERS_DISABLE_LOCAL_AUTH=false`; OIDC issuer and button label remain present.

- [ ] **Step 2: Verify the secret is still present without printing it**

Run:

```bash
docker inspect ryot --format '{{range .Config.Env}}{{println .}}{{end}}' | rg '^SERVER_OIDC_CLIENT_SECRET=' >/dev/null && printf 'SERVER_OIDC_CLIENT_SECRET=present\n' || printf 'SERVER_OIDC_CLIENT_SECRET=absent\n'
```

Expected: `SERVER_OIDC_CLIENT_SECRET=present`

- [ ] **Step 3: Verify the auth page no longer reports a total lockout**

Run:

```bash
curl -k -fsS https://ryot.home.lab/auth | rg 'Authentication disabled|Both local authentication and OpenID Connect are disabled' || true
```

Expected after fix: no matching disabled-auth alert text.

- [ ] **Step 4: Add the Linear final update**

Comment on OPN-250 with:

```markdown
Outcome: done or blocked.

What changed:
- Removed/corrected the stale Ryot auth env override in the Komodo media stack, or explain why that could not be done.

Verification:
- `docker compose --env-file apps/media/example.env -f apps/media/compose.yml config --format json | jq -r '.services.ryot.environment.USERS_DISABLE_LOCAL_AUTH'`
- `docker inspect ryot --format '{{range .Config.Env}}{{println .}}{{end}}' | rg '^(USERS_DISABLE_LOCAL_AUTH|SERVER_OIDC_ISSUER_URL|FRONTEND_OIDC_BUTTON_LABEL)='`
- `curl -k -fsS https://ryot.home.lab/auth | rg 'Authentication disabled|Both local authentication and OpenID Connect are disabled' || true`

Commit/branch:
- No code commit if only Komodo env changed.

Remaining follow-ups:
- None, or the exact Komodo access/action needed.
```

## Self-Review

- Spec coverage: The plan covers the reported disabled auth page, the stale live `USERS_DISABLE_LOCAL_AUTH=true`, the repo default `false`, Komodo env correction, redeploy, and post-fix verification.
- Placeholder scan: No placeholder implementation steps remain; the only conditional language is for the final Linear outcome because it depends on Komodo access.
- Type consistency: No code interfaces are introduced.
