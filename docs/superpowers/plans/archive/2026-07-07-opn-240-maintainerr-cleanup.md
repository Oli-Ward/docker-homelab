# OPN-240 Maintainerr Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Maintainerr as the chosen watched-media cleanup tool and document the safe deployment/configuration path for destructive cleanup.

**Architecture:** Maintainerr runs in the existing arr stack, stores mutable rule/action state under `${APPDATA_ROOT}/maintainerr`, and is exposed through the existing NPM plus Authentik pattern. Cleanup rules, keep lists, candidate collections, and deletion actions live in Maintainerr UI/appdata, while the repo records only durable deployment wiring and operator runbooks.

**Tech Stack:** Docker Compose, Maintainerr, Jellyfin, Sonarr, Radarr, Jellyseerr, Nginx Proxy Manager, Authentik, AdGuard, Homepage, Markdown, Linear.

---

## Global Constraints

- Do not run `docker compose up`, `docker compose down`, `docker compose pull`, or restart containers directly.
- Do not mutate live Docker, Komodo, NPM, Authentik, AdGuard, Jellyfin, Sonarr, Radarr, Jellyseerr, or Maintainerr state.
- Do not read or commit `.env` files, API keys, passwords, cookies, session files, databases, or app runtime state.
- Treat `${APPDATA_ROOT}/maintainerr` as mutable app state outside repo management.
- Treat cleanup as destructive automation: start with candidate collection review before enabling deletion handling.
- Maintainerr has a UI, so external access must include NPM, Authentik, AdGuard, and Homepage follow-up work.

### Task 1: Add Maintainerr To The Arr Stack

**Files:**
- Modify: `apps/arr-stack/compose.yml`

- [ ] **Step 1: Add the Maintainerr service**

Add this service after `bazarr-sync` and before `autoscan`:

```yaml
  # Maintainerr - Watched media cleanup
  maintainerr:
    image: ghcr.io/maintainerr/maintainerr:latest
    container_name: maintainerr
    user: "${PUID}:${PGID}"
    environment:
      - TZ=${TZ}
    volumes:
      - ${APPDATA_ROOT}/maintainerr:/opt/data
    restart: unless-stopped
    networks:
      - media_net
      - proxy_net
```

Expected: Maintainerr can reach Jellyfin, Sonarr, Radarr, and Jellyseerr by Docker service name through `media_net`, and NPM can reach Maintainerr through `proxy_net`.

- [ ] **Step 2: Do not add host port publishing**

Confirm the service has no `ports:` block.

Expected: browser access is routed through NPM/Auth, not direct host port exposure.

### Task 2: Add Dashboard Visibility

**Files:**
- Modify: `apps/utilities/homepage/services.yaml`

- [ ] **Step 1: Add a Maintainerr entry**

Add this entry under `Download Management`, after `Bazarr Sync Job`:

```yaml
    - Maintainerr:
        icon: mdi-delete-clock
        href: https://maintainerr.home.lab
        description: Watched media cleanup
        siteMonitor: http://maintainerr:6246/api/health/ready
```

Expected: Homepage links to the Authentik-protected external URL and uses an internal health endpoint for basic visibility.

### Task 3: Update Service Catalog

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add Maintainerr to Management services**

Add this bullet under `### Management`:

```markdown
* Maintainerr - Watched media cleanup
```

- [ ] **Step 2: Add the Maintainerr domain**

Add this bullet under the domains examples:

```markdown
* `maintainerr.home.lab`
```

- [ ] **Step 3: Record the UI exposure requirement**

Add this note under `## ⚠️ Notes`:

```markdown
* Maintainerr must be exposed through Nginx Proxy Manager and protected by Authentik proxy auth before browser use.
```

Expected: README makes Maintainerr visible in the service catalog and preserves the established exposure pattern.

### Task 4: Write The Maintainerr Runbook

**Files:**
- Create: `diagnostics/build-lanes/2026-07-07-opn-240-maintainerr-cleanup.md`

- [ ] **Step 1: Document deployment checklist**

Create the runbook with:

```markdown
# OPN-240 Maintainerr Cleanup Runbook

## Chosen Approach

Use Maintainerr for watched-media cleanup. Do not build custom OpenClaw, gateway, or filesystem deletion logic for the first version.

## Repo-Managed Wiring

- Compose service: `maintainerr` in `apps/arr-stack/compose.yml`
- Image: `ghcr.io/maintainerr/maintainerr:latest`
- App state: `${APPDATA_ROOT}/maintainerr:/opt/data`
- Runtime user: `${PUID}:${PGID}`
- Networks: `media_net`, `proxy_net`
- Internal URL: `http://maintainerr:6246`
- Health endpoint: `http://maintainerr:6246/api/health/ready`

## Required External UI Work

1. Komodo: redeploy the arr stack from this repo after review.
2. AdGuard: add or verify `maintainerr.home.lab`.
3. Nginx Proxy Manager: add a proxy host for `maintainerr.home.lab` to upstream `http://maintainerr:6246`.
4. Authentik: protect `https://maintainerr.home.lab` with proxy auth before normal browser use.
5. Homepage: verify the Maintainerr link and health monitor.

## Maintainerr Initial Setup

1. Open `https://maintainerr.home.lab` only after Authentik and NPM are configured.
2. Configure Jellyfin as the media server using internal Docker networking where possible.
3. Configure Radarr with `http://radarr:7878` and the real API key from Radarr UI or untracked secret storage.
4. Configure Sonarr with `http://sonarr:8989` and the real API key from Sonarr UI or untracked secret storage.
5. Configure Jellyseerr with `http://jellyseerr:5055` if request cleanup is enabled.
6. Do not commit API keys, tokens, exported Maintainerr state, or screenshots containing secrets.

## Conservative Cleanup Policy

Start with non-destructive collection review:

- Movies: watched in Jellyfin, older than the chosen minimum age, not in protected collections, then held in a Maintainerr collection for a grace period before action.
- TV: season-level cleanup for the first version. Do not delete individual watched episodes until the season-level behavior is proven too coarse.
- Exclusions: protect favorites, pinned/manual keep items, protected collections, and protected paths before enabling handling.
- Handling: configure Maintainerr to update Radarr/Sonarr monitoring or remove items in a way that prevents automatic re-download.

## Enablement Gate

Do not enable destructive handling until:

- Candidate collections have been reviewed.
- At least one movie and one TV-season sample match exactly as expected.
- Exclusions have been tested.
- A recent backup or recovery path exists for the relevant app state and media.

## Recovery

- Remove or adjust the Maintainerr rule or exclusion that selected the item.
- Re-monitor the item in Radarr/Sonarr only if it should be downloadable again.
- Re-request through Jellyseerr if appropriate.
- Restore from backup when the original deleted file is needed and re-download is not desired.
```

Expected: the runbook is operator-ready and contains no real secrets.

### Task 5: Validate The Repo Change

**Files:**
- Check: `apps/arr-stack/compose.yml`
- Check: `apps/utilities/homepage/services.yaml`
- Check: `README.md`
- Check: `diagnostics/build-lanes/2026-07-07-opn-240-maintainerr-cleanup.md`
- Check: `docs/superpowers/specs/2026-07-07-opn-240-maintainerr-cleanup-design.md`
- Check: `docs/superpowers/plans/2026-07-07-opn-240-maintainerr-cleanup.md`

- [ ] **Step 1: Check formatting**

Run:

```bash
git diff --check
```

Expected: no whitespace errors.

- [ ] **Step 2: Render the arr stack Compose config**

Run:

```bash
env PUID=1000 PGID=1000 TZ=Pacific/Auckland DATA_ROOT=/data APPDATA_ROOT=/srv/appdata BAZARR_SYNC_URL=http://bazarr:6767 BAZARR_SYNC_API_TOKEN=change-me docker compose -f apps/arr-stack/compose.yml --profile manual config
```

Expected: Compose renders without deploying anything. The rendered Maintainerr service has image `ghcr.io/maintainerr/maintainerr:latest`, user `1000:1000`, `/srv/appdata/maintainerr:/opt/data`, and no published host port.

- [ ] **Step 3: Scan changed OPN-240 files for accidental secrets**

Run:

```bash
rg -n "password|token|secret|api[_-]?key|cookie|authorization|privkey|BEGIN " docs/superpowers/specs/2026-07-07-opn-240-maintainerr-cleanup-design.md docs/superpowers/plans/2026-07-07-opn-240-maintainerr-cleanup.md diagnostics/build-lanes/2026-07-07-opn-240-maintainerr-cleanup.md apps/arr-stack/compose.yml apps/utilities/homepage/services.yaml README.md
```

Expected: only generic placeholder or instruction references appear; no real secret values.

### Task 6: Update Linear

**Files:**
- Update: Linear `OPN-240`

- [ ] **Step 1: Add final Linear comment**

Add this final comment:

```markdown
Outcome: repo-side Maintainerr deployment wiring and operator runbook are ready; live deployment/configuration remains manual.

What changed:
- Chose Maintainerr as the watched-media cleanup approach instead of custom gateway/OpenClaw deletion logic.
- Added Maintainerr to the arr stack with persistent app state under `${APPDATA_ROOT}/maintainerr`.
- Added Homepage visibility for `https://maintainerr.home.lab`.
- Documented the required Komodo, NPM, Authentik, AdGuard, and Maintainerr UI setup.
- Defined the initial cleanup policy: movie cleanup after watched + grace period, TV cleanup at season level, candidate review before destructive handling, and explicit exclusions.

Verification:
- `git diff --check`
- `docker compose -f apps/arr-stack/compose.yml --profile manual config` with placeholder env values
- secret scan across the OPN-240 files and touched repo files

Remaining follow-ups:
- Redeploy the arr stack through Komodo.
- Add `maintainerr.home.lab` in AdGuard.
- Add an NPM proxy host to `http://maintainerr:6246`.
- Protect the UI with Authentik proxy auth.
- Configure Maintainerr integrations and review candidate collections before enabling deletion handling.
```

- [ ] **Step 2: Move Linear to In Review**

Move `OPN-240` to `In Review` after repo-side verification passes. Do not move it to `Done` until live Maintainerr deployment and destructive-cleanup safety checks have been completed.

