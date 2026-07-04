# OPN-224 Authentik Media Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the media-server Authentik path so the affected media service is reachable only through the intended authenticated route.

**Architecture:** Treat Docker Compose as the container/network source of truth and Nginx Proxy Manager plus Authentik as the live routing/auth source of truth. Current evidence points to Jellyseerr: NPM has a proxy host for `request.home.lab` with no Authentik `auth_request`, while the expected/dashboard URL is `jellyseerr.home.lab` and Authentik does not load a Jellyseerr application. The fix should be a narrow NPM/Auth configuration change, followed by read-only HTTP and log verification.

**Tech Stack:** Docker Compose, Nginx Proxy Manager, Authentik proxy provider/outpost, Jellyseerr, curl, Docker read-only diagnostics.

---

### Task 1: Record Baseline And Root Cause

**Files:**
- Create: `diagnostics/build-lanes/2026-07-04-opn-224-authentik-media-auth.md`

- [ ] **Step 1: Create the diagnostic report**

Create `diagnostics/build-lanes/2026-07-04-opn-224-authentik-media-auth.md` with:

```markdown
# OPN-224 Authentik Media Auth Diagnosis

Date: 2026-07-04

## Scope

Investigate the media-server Authentik authentication path for protected media services without mutating Docker, NPM, Authentik, DNS, certificates, or app containers.

## Evidence

Read-only container inventory showed:

- `authentik-server` and `authentik-worker-1` are up and healthy.
- `nginx-proxy-manager` is up.
- `jellyseerr` is up and attached to `media_net` and `proxy_net`.
- `sonarr`, `radarr`, `prowlarr`, and `bazarr` are up.

HTTP header checks showed:

- `https://sonarr.home.lab` returns an Authentik 302 to `/outpost.goauthentik.io/start`.
- `https://radarr.home.lab` returns an Authentik 302 to `/outpost.goauthentik.io/start`.
- `https://prowlarr.home.lab` returns an Authentik 302 to `/outpost.goauthentik.io/start`.
- `https://bazarr.home.lab` returns an Authentik 302 to `/outpost.goauthentik.io/start`.
- `https://auth.home.lab` returns an Authentik 302 to the authentication flow.
- `https://jellyseerr.home.lab` fails TLS SNI before HTTP with `tlsv1 unrecognized name`.
- `https://request.home.lab` reaches Jellyseerr directly and returns `307 Temporary Redirect` to `/login`.

NPM generated config showed:

- Jellyseerr is configured as proxy host `request.home.lab`, upstream `jellyseerr:5055`.
- That NPM host has no `auth_request` block.
- No generated NPM proxy host exists for `jellyseerr.home.lab`.
- Other protected media hosts such as `sonarr.home.lab`, `radarr.home.lab`, `prowlarr.home.lab`, and `bazarr.home.lab` include Authentik `auth_request` config.

Authentik logs showed:

- Loaded applications include `sonarr.home.lab`, `radarr.home.lab`, `prowlarr.home.lab`, `bazarr.home.lab`, and other protected services.
- No loaded Jellyseerr application was observed in recent outpost logs.

## Root Cause

The affected service is Jellyseerr. The intended route used by repo-managed Homepage is `https://jellyseerr.home.lab`, but live NPM has Jellyseerr configured as `request.home.lab`. Because `jellyseerr.home.lab` is not present as an NPM TLS proxy host, TLS fails before Authentik can run. The existing `request.home.lab` route reaches Jellyseerr directly without Authentik forward-auth protection.

## Required Fix

Use Nginx Proxy Manager and Authentik UI/API to create or update the Jellyseerr protected route:

- Public host: `jellyseerr.home.lab`
- Upstream: `http://jellyseerr:5055`
- Authentik application/provider/outpost host: `jellyseerr.home.lab`
- NPM advanced config: same Authentik forward-auth pattern used by Sonarr/Radarr/Prowlarr/Bazarr.

Decide whether `request.home.lab` should be removed, disabled, or redirected to `jellyseerr.home.lab`. It should not remain as an unauthenticated direct Jellyseerr route.

## Verification

After the live NPM/Auth changes:

```bash
curl -k -sS -I --max-time 10 https://jellyseerr.home.lab
curl -k -sS -I --max-time 10 https://request.home.lab || true
docker logs --tail 120 authentik-server 2>&1 | rg -i 'jellyseerr|request.home.lab|outpost.goauthentik|error|warning'
docker exec nginx-proxy-manager sh -lc "grep -R \"server_name jellyseerr.home.lab\\|server_name request.home.lab\\|auth_request\\|outpost.goauthentik\" -n /data/nginx/proxy_host 2>/dev/null"
```

Expected:

- `jellyseerr.home.lab` returns an Authentik 302 to `/outpost.goauthentik.io/start` for an unauthenticated request.
- Authentik outpost logs include a loaded Jellyseerr application for `jellyseerr.home.lab`.
- NPM generated config for `jellyseerr.home.lab` includes the Authentik `auth_request` block.
- `request.home.lab` is disabled, redirects, or is also Authentik-protected; it must not expose direct Jellyseerr login unauthenticated.

## Rollback

If the new route breaks access, revert the live NPM proxy host and Authentik application/provider/outpost changes to their previous values. Do not restart or redeploy Docker containers unless the operator explicitly approves it.
```

- [ ] **Step 2: Verify the report contains no secrets**

Run:

```bash
rg -n "token|secret|password|api[_-]?key|cookie|authorization|privkey|BEGIN " diagnostics/build-lanes/2026-07-04-opn-224-authentik-media-auth.md
```

Expected: no matches, except generic words if they are not values. If any value appears, remove it before continuing.

### Task 2: Apply The Live NPM/Auth Fix

**Files:**
- External UI/API: Nginx Proxy Manager
- External UI/API: Authentik
- Check: `apps/utilities/homepage/services.yaml`

- [ ] **Step 1: Confirm the canonical Jellyseerr host**

Run:

```bash
rg -n "Jellyseerr|jellyseerr.home.lab|request.home.lab" README.md apps/utilities/homepage/services.yaml apps/media/compose.yml
```

Expected: Homepage points users at `https://jellyseerr.home.lab`; no repo-managed dashboard entry points to `request.home.lab`.

- [ ] **Step 2: Update NPM for Jellyseerr**

In Nginx Proxy Manager, create or update the Jellyseerr proxy host:

```text
Domain Names: jellyseerr.home.lab
Scheme: http
Forward Hostname / IP: jellyseerr
Forward Port: 5055
Websockets Support: enabled
SSL Certificate: homelab certificate covering jellyseerr.home.lab
Force SSL: enabled
HTTP/2 Support: match the working media hosts
HSTS: match the working media hosts
```

Copy the Authentik advanced configuration pattern from one working protected media host, preferably `sonarr.home.lab`, and adjust only the host-specific values if present. The generated NPM config must include:

```nginx
auth_request /_auth;
location /outpost.goauthentik.io {
    proxy_pass http://authentik-server:9000/outpost.goauthentik.io;
}
```

- [ ] **Step 3: Update Authentik for Jellyseerr**

In Authentik, create or update the Jellyseerr application/provider/outpost entry:

```text
Application name: jellyseerr
External host: https://jellyseerr.home.lab
Provider type: Proxy Provider
Mode: Forward auth / single application, matching the other media services
Outpost: the same embedded/outpost used by Sonarr/Radarr/Prowlarr/Bazarr
Policy/group access: match the other protected media services
```

Expected: Authentik outpost reloads and logs a loaded application for `jellyseerr.home.lab`.

- [ ] **Step 4: Disable or protect the legacy request host**

In NPM and Authentik, decide and apply one of these outcomes for `request.home.lab`:

```text
Preferred: disable/remove request.home.lab after jellyseerr.home.lab works.
Acceptable: redirect request.home.lab to https://jellyseerr.home.lab.
Acceptable: protect request.home.lab with the same Authentik forward-auth config.
Not acceptable: leave request.home.lab as a direct unauthenticated Jellyseerr login route.
```

### Task 3: Verify The Fixed Auth Flow

**Files:**
- Check: live NPM generated config
- Check: live Authentik logs
- Check: Linear `OPN-224`

- [ ] **Step 1: Verify unauthenticated Jellyseerr redirects to Authentik**

Run:

```bash
curl -k -sS -I --max-time 10 https://jellyseerr.home.lab | sed -n '1,16p'
```

Expected:

```text
HTTP/2 302
location: https://jellyseerr.home.lab/outpost.goauthentik.io/start?rd=https://jellyseerr.home.lab/
```

- [ ] **Step 2: Verify the legacy route is not direct**

Run:

```bash
curl -k -sS -I --max-time 10 https://request.home.lab | sed -n '1,16p' || true
```

Expected one of:

```text
HTTP/2 301
location: https://jellyseerr.home.lab/
```

or:

```text
HTTP/2 302
location: https://request.home.lab/outpost.goauthentik.io/start?rd=https://request.home.lab/
```

or a disabled-host TLS/HTTP failure if the route was intentionally removed.

- [ ] **Step 3: Verify Authentik loaded Jellyseerr**

Run:

```bash
docker logs --tail 160 authentik-server 2>&1 | rg -i 'Loaded application|jellyseerr|request.home.lab|error|warning'
```

Expected: a `Loaded application` entry for Jellyseerr with host `jellyseerr.home.lab`, and no new Jellyseerr-related error.

- [ ] **Step 4: Verify NPM generated Authentik config**

Run:

```bash
docker exec nginx-proxy-manager sh -lc "grep -R \"server_name jellyseerr.home.lab\\|server_name request.home.lab\\|auth_request\\|outpost.goauthentik\" -n /data/nginx/proxy_host 2>/dev/null"
```

Expected: the `jellyseerr.home.lab` proxy host includes `auth_request` and `outpost.goauthentik` blocks.

- [ ] **Step 5: Record final Linear update**

Post a Linear comment:

```markdown
Outcome: done

Root cause:
- Jellyseerr was live in NPM as `request.home.lab` without Authentik forward auth.
- The intended/dashboard route `jellyseerr.home.lab` had no NPM TLS proxy host, so TLS failed before Authentik.

Changed:
- Added/updated Jellyseerr NPM proxy host for `jellyseerr.home.lab`.
- Added/updated Authentik Jellyseerr application/provider/outpost binding.
- Removed, redirected, or Authentik-protected `request.home.lab`.

Verification:
- `curl -k -I https://jellyseerr.home.lab` returned Authentik 302.
- Authentik outpost logs loaded Jellyseerr for `jellyseerr.home.lab`.
- NPM generated config includes Authentik `auth_request`.
- `request.home.lab` no longer exposes direct Jellyseerr login.

Commit/PR:
- None unless a diagnostic doc was committed.

Remaining follow-ups:
- None, unless Oli wants `request.home.lab` retained as an alias.
```

Then move `OPN-224` to `Done`.
