# OPN-246 Mediastarr Media Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evaluate and, if safe, add Mediastarr as an internal media automation helper for Sonarr/Radarr missing-content and upgrade searches.

**Architecture:** Mediastarr belongs in `apps/arr-stack` because it integrates with Sonarr/Radarr and may overlap with Maintainerr, Recyclarr, Seekarr, and Seerr. Start internal-first on `media_net`; add `proxy_net`, NPM, AuthentiK, and Homepage only if the verified app has a useful web UI and the user approves exposure.

**Tech Stack:** Docker Compose, Mediastarr upstream `kroeberd/mediastarr` pending execution-time verification, Sonarr, Radarr, optional Discord notifications, Komodo.

## Global Constraints

- Verify upstream source, Docker image, maintenance state, and docs before adding a service.
- Do not install a random image or copy commands from untrusted blogs.
- Komodo is the source of truth for deployment; do not run deploy/restart/pull commands directly without explicit permission.
- Do not commit API keys, Discord webhook URLs, real `.env` values, SQLite runtime state, or app config containing secrets.
- Default to internal-only until the app proves useful.
- Disable destructive/noisy automation until manual dry-run/test behavior is understood.
- Avoid fighting Recyclarr-managed quality profiles and Maintainerr cleanup rules.

---

## File Structure

- Modify `apps/arr-stack/compose.yml`: add `mediastarr` only after upstream verification.
- Modify `apps/arr-stack/example.env`: document Mediastarr API key placeholders.
- Modify `apps/utilities/homepage/services.yaml`: add Mediastarr only if a web UI is exposed.
- Modify `README.md`: add service and safety notes only if installed.
- Create `docs/automation/mediastarr.md`: record verification result, overlap decision, and enabled automation scope.

## Sources Checked

- Candidate Mediastarr GitHub found: https://github.com/kroeberd/mediastarr

### Task 1: Verify upstream and decide install/no-install

**Files:**
- Create: `docs/automation/mediastarr.md`

**Interfaces:**
- Consumes: ticket requirement to verify source/image/docs before installation.
- Produces: durable decision record saying install, defer, or reject.

- [x] **Step 1: Verify candidate upstream**

Open `https://github.com/kroeberd/mediastarr` and record:

```text
repository owner/name: kroeberd/mediastarr
license: record exact license from repository
latest release/tag: record exact release or tag
latest commit date: record exact date
official image registry/name: record exact image name from repository docs
supported integrations: Sonarr, Radarr, Discord, web UI if present
risky actions: missing searches, quality upgrade searches, monitor changes, deletes, webhook notifications
```

- [x] **Step 2: Decide overlap with existing services**

Add this section to `docs/automation/mediastarr.md`:

```markdown
# Mediastarr Evaluation

## Upstream Verification

- Repository: https://github.com/kroeberd/mediastarr
- Official image: `kroeberd/mediastarr:latest` per upstream README
- Selected tag: `latest` initially, with latest GitHub release noted as `v7.1.12` on 2026-05-17
- License: MIT
- Maintenance check: latest release shown as `v7.1.12` on 2026-05-17

## Fit Decision

Mediastarr overlaps with Seekarr for missing-content and quality-upgrade searches. It must not be enabled for scheduled writes until Recyclarr ownership of quality profiles and Maintainerr ownership of cleanup are documented.

Decision:

- Install status: pending verification
- Initial exposure: internal only
- Initial automation: dry-run/manual only
- Replacement/companion decision vs Seekarr: pending OPN-247 comparison
```

- [ ] **Step 3: Stop if verification fails**

If no trustworthy official image or active upstream exists, do not edit Compose. Update Linear with:

```markdown
Blocked: Mediastarr upstream/image could not be verified safely. I did not install a container or add repo config. Next action: provide trusted upstream docs or choose a maintained alternative.
```

- [x] **Step 4: Commit evaluation record**

```bash
git add docs/automation/mediastarr.md
git commit -m "OPN-246: record Mediastarr evaluation"
```

### Task 2: Add internal-only Mediastarr service if verification passes

**Files:**
- Modify: `apps/arr-stack/compose.yml`
- Modify: `apps/arr-stack/example.env`
- Modify: `docs/automation/mediastarr.md`

**Interfaces:**
- Consumes: verified official image/tag from Task 1.
- Produces: internal Mediastarr service with secrets injected from `.env`.

- [x] **Step 1: Add env placeholders**

Append to `apps/arr-stack/example.env`:

```env

# Mediastarr automation helper
MEDIASTARR_SONARR_URL=http://sonarr:8989
MEDIASTARR_RADARR_URL=http://radarr:7878
MEDIASTARR_SONARR_API_KEY=change-me
MEDIASTARR_RADARR_API_KEY=change-me
MEDIASTARR_DISCORD_WEBHOOK_URL=
```

- [x] **Step 2: Add Compose service using verified image/tag**

After Task 1, replace `VERIFIED_IMAGE_AND_TAG_FROM_DOCS` in the snippet before editing; do not leave that string in the file.

```yaml
  # Mediastarr - missing content and quality upgrade search helper
  mediastarr:
    image: kroeberd/mediastarr:latest
    container_name: mediastarr
    environment:
      - TZ=${TZ}
      - PUID=${PUID}
      - PGID=${PGID}
      - SONARR_URL=${MEDIASTARR_SONARR_URL}
      - RADARR_URL=${MEDIASTARR_RADARR_URL}
      - SONARR_API_KEY=${MEDIASTARR_SONARR_API_KEY}
      - RADARR_API_KEY=${MEDIASTARR_RADARR_API_KEY}
      - DISCORD_WEBHOOK_URL=${MEDIASTARR_DISCORD_WEBHOOK_URL}
    volumes:
      - ${APPDATA_ROOT}/mediastarr:/data
    restart: unless-stopped
    networks:
      - media_net
``` 

- [x] **Step 3: Validate Compose without deploying**

Run from `apps/arr-stack` with safe placeholders and the verified image present in the file:

```bash
PUID=1000 PGID=1000 TZ=Pacific/Auckland DATA_ROOT=/data APPDATA_ROOT=/srv/appdata BAZARR_SYNC_URL=http://bazarr:6767 BAZARR_SYNC_API_TOKEN=change-me MEDIASTARR_SONARR_URL=http://sonarr:8989 MEDIASTARR_RADARR_URL=http://radarr:7878 MEDIASTARR_SONARR_API_KEY=change-me MEDIASTARR_RADARR_API_KEY=change-me MEDIASTARR_DISCORD_WEBHOOK_URL= docker compose config
```

Expected: PASS, rendered `mediastarr` service is attached to `media_net` only.

- [x] **Step 4: Update evaluation record**

In `docs/automation/mediastarr.md`, replace pending fields with exact values and add:

```markdown
## Initial Runtime Policy

- Keep internal-only on `media_net` for first evaluation.
- Do not schedule automatic searches until one manual dry-run/test search is reviewed.
- Do not enable delete, unmonitor, or quality-profile mutation behavior.
- Recyclarr remains owner of TRaSH/profile/custom-format sync.
- Maintainerr remains owner of watched-media cleanup.
```

- [x] **Step 5: Commit service changes**

```bash
git add apps/arr-stack/compose.yml apps/arr-stack/example.env docs/automation/mediastarr.md
git commit -m "OPN-246: add Mediastarr internal service"
```

### Task 3: Optional UI exposure after manual approval

**Files:**
- Modify: `apps/arr-stack/compose.yml`
- Modify: `apps/utilities/homepage/services.yaml`
- Modify: `README.md`

**Interfaces:**
- Consumes: confirmed Mediastarr UI port from upstream docs.
- Produces: NPM/AuthentiK/Homepage checklist for exposed UI.

- [x] **Step 1: Confirm UI port and auth model**

Record in `docs/automation/mediastarr.md`:

```markdown
## UI Exposure Decision

- UI exists: yes/no
- UI port: `7979`
- Native auth exists: yes/no
- Exposure approved by user: yes/no
```

- [x] **Step 2: If approved, add `proxy_net`**

Only after user approval, add `proxy_net` to the `mediastarr` service networks:

```yaml
    networks:
      - media_net
      - proxy_net
```

- [x] **Step 3: Add Homepage entry if exposed**

Add under `Download Management`:

```yaml
    - Mediastarr:
        icon: mdi-movie-cog
        href: https://mediastarr.home.lab
        description: Media search automation helper
        siteMonitor: http://mediastarr:7979
```


- [x] **Step 4: Record external UI checklist**

Add to `docs/automation/mediastarr.md`:

```markdown
## External UI Checklist

- NPM host: `mediastarr.home.lab` -> `mediastarr:<verified-port>`.
- AuthentiK application/provider/outpost entry: `Mediastarr`.
- AdGuard DNS record: `mediastarr.home.lab` to NPM host.
- Homepage entry added only after the route works.
```

- [x] **Step 5: Commit exposure/docs changes**

```bash
git add apps/arr-stack/compose.yml apps/utilities/homepage/services.yaml README.md docs/automation/mediastarr.md
git commit -m "OPN-246: expose Mediastarr UI"
```
