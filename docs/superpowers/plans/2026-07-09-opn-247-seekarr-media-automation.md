# OPN-247 Seekarr Media Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evaluate and, if safe, add Seekarr as the preferred missing-media search automation companion/replacement for Huntarr-style workflows.

**Architecture:** Seekarr belongs in `apps/arr-stack` because it integrates with Sonarr/Radarr and overlaps with Mediastarr, Maintainerr, Recyclarr, and Seerr. Start with internal-only dry-run behavior on `media_net`; expose UI only if upstream confirms a UI and the user approves the NPM/AuthentiK route.

**Tech Stack:** Docker Compose, Seekarr candidate upstream `tumeden/seekarr`, Sonarr, Radarr, optional Jellyfin/Seerr context, Komodo.

## Global Constraints

- Verify official source, Docker image, docs, and maintenance state before installation.
- Do not install a random image or use unverified registry names.
- Komodo is the source of truth for deployment; do not run deploy/restart/pull commands directly without explicit permission.
- Do not commit API keys, real `.env`, app databases, runtime state, or generated config containing secrets.
- Prefer dry-run/manual search first; do not enable scheduled automation until reviewed.
- Avoid fighting Maintainerr cleanup decisions, Recyclarr quality-profile management, and Seerr request behavior.

---

## File Structure

- Modify `apps/arr-stack/compose.yml`: add `seekarr` only after upstream verification.
- Modify `apps/arr-stack/example.env`: document Seekarr placeholders.
- Modify `apps/utilities/homepage/services.yaml`: add Seekarr only if a UI is exposed.
- Modify `README.md`: add service and safety notes only if installed.
- Create `docs/automation/seekarr.md`: record verification result, Mediastarr comparison, and enabled automation scope.

## Sources Checked

- Candidate Seekarr GitHub found: https://github.com/tumeden/seekarr

### Task 1: Verify upstream and compare against Mediastarr

**Files:**
- Create: `docs/automation/seekarr.md`

**Interfaces:**
- Consumes: ticket requirement to verify source/image/docs and compare with Mediastarr.
- Produces: durable decision record saying install, defer, reject, or prefer over Mediastarr.

- [ ] **Step 1: Verify candidate upstream**

Open `https://github.com/tumeden/seekarr` and record:

```text
repository owner/name: tumeden/seekarr
license: record exact license from repository
latest release/tag: record exact release or tag
latest commit date: record exact date
official image registry/name: record exact image name from repository docs
supported integrations: Sonarr, Radarr, Seerr/Jellyseerr, Jellyfin/Plex if present
risky actions: missing searches, upgrades, monitor changes, deletes, request changes
safety features: dry-run mode, rate limiting, schedule controls
```

- [ ] **Step 2: Create evaluation record**

Create `docs/automation/seekarr.md`:

```markdown
# Seekarr Evaluation

## Upstream Verification

- Repository: https://github.com/tumeden/seekarr
- Official image: `ghcr.io/tumeden/seekarr:latest` or `tumeden/seekarr:latest` per upstream README
- Selected tag: `latest` initially, with latest GitHub release noted as `v0.5.0` on 2026-06-30
- License: MIT
- Maintenance check: latest release shown as `v0.5.0 - UI changes / Code restructure` on 2026-06-30

## Fit Decision

Seekarr overlaps with Mediastarr for missing-content and upgrade searches. It must not be enabled for scheduled writes until Recyclarr ownership of quality profiles, Maintainerr ownership of cleanup, and Seerr ownership of requests are documented.

Decision:

- Install status: pending verification
- Initial exposure: internal only
- Initial automation: dry-run/manual only
- Replacement/companion decision vs Mediastarr: pending OPN-246 comparison
```

- [ ] **Step 3: Stop if verification fails**

If no trustworthy official image or active upstream exists, do not edit Compose. Update Linear with:

```markdown
Blocked: Seekarr upstream/image could not be verified safely. I did not install a container or add repo config. Next action: provide trusted upstream docs or choose a maintained alternative.
```

- [ ] **Step 4: Commit evaluation record**

```bash
git add docs/automation/seekarr.md
git commit -m "OPN-247: record Seekarr evaluation"
```

### Task 2: Add internal-only Seekarr service if verification passes

**Files:**
- Modify: `apps/arr-stack/compose.yml`
- Modify: `apps/arr-stack/example.env`
- Modify: `docs/automation/seekarr.md`

**Interfaces:**
- Consumes: verified official image/tag from Task 1.
- Produces: internal Seekarr service with secrets injected from `.env`.

- [ ] **Step 1: Add env placeholders**

Append to `apps/arr-stack/example.env`:

```env

# Seekarr missing media automation helper
SEEKARR_SONARR_URL=http://sonarr:8989
SEEKARR_RADARR_URL=http://radarr:7878
SEEKARR_SONARR_API_KEY=change-me
SEEKARR_RADARR_API_KEY=change-me
SEEKARR_DRY_RUN=true
SEEKARR_SCHEDULE=0 4 * * *
```

- [ ] **Step 2: Add Compose service using verified image/tag**

After Task 1, replace `VERIFIED_IMAGE_AND_TAG_FROM_DOCS` before editing; do not leave that string in the file.

```yaml
  # Seekarr - missing media search automation helper
  seekarr:
    image: ghcr.io/tumeden/seekarr:latest
    container_name: seekarr
    environment:
      - TZ=${TZ}
      - PUID=${PUID}
      - PGID=${PGID}
      - SONARR_URL=${SEEKARR_SONARR_URL}
      - RADARR_URL=${SEEKARR_RADARR_URL}
      - SONARR_API_KEY=${SEEKARR_SONARR_API_KEY}
      - RADARR_API_KEY=${SEEKARR_RADARR_API_KEY}
      - DRY_RUN=${SEEKARR_DRY_RUN}
      - SCHEDULE=${SEEKARR_SCHEDULE}
    volumes:
      - ${APPDATA_ROOT}/seekarr:/config
    restart: unless-stopped
    networks:
      - media_net
```

- [ ] **Step 3: Validate Compose without deploying**

Run from `apps/arr-stack` with safe placeholders and the verified image present in the file:

```bash
PUID=1000 PGID=1000 TZ=Pacific/Auckland DATA_ROOT=/data APPDATA_ROOT=/srv/appdata BAZARR_SYNC_URL=http://bazarr:6767 BAZARR_SYNC_API_TOKEN=change-me SEEKARR_SONARR_URL=http://sonarr:8989 SEEKARR_RADARR_URL=http://radarr:7878 SEEKARR_SONARR_API_KEY=change-me SEEKARR_RADARR_API_KEY=change-me SEEKARR_DRY_RUN=true SEEKARR_SCHEDULE='0 4 * * *' docker compose config
```

Expected: PASS, rendered `seekarr` service is attached to `media_net` only and dry-run is enabled.

- [ ] **Step 4: Update evaluation record**

In `docs/automation/seekarr.md`, replace pending fields with exact values and add:

```markdown
## Initial Runtime Policy

- Keep internal-only on `media_net` for first evaluation.
- Start with `SEEKARR_DRY_RUN=true`.
- Do not enable automatic downloads until one manual dry-run/test search is reviewed.
- Recyclarr remains owner of TRaSH/profile/custom-format sync.
- Maintainerr remains owner of watched-media cleanup.
- Seerr remains owner of user request workflows.
```

- [ ] **Step 5: Commit service changes**

```bash
git add apps/arr-stack/compose.yml apps/arr-stack/example.env docs/automation/seekarr.md
git commit -m "OPN-247: add Seekarr internal service"
```

### Task 3: Optional UI exposure and final replacement decision

**Files:**
- Modify: `apps/arr-stack/compose.yml`
- Modify: `apps/utilities/homepage/services.yaml`
- Modify: `README.md`
- Modify: `docs/automation/seekarr.md`

**Interfaces:**
- Consumes: confirmed Seekarr UI port and OPN-246 Mediastarr evaluation.
- Produces: documented route if exposed and a clear decision on Seekarr vs Mediastarr.

- [ ] **Step 1: Confirm UI and auth model**

Record in `docs/automation/seekarr.md`:

```markdown
## UI Exposure Decision

- UI exists: yes/no
- UI port: `8788`
- Native auth exists: yes/no
- Exposure approved by user: yes/no
```

- [ ] **Step 2: If approved, add `proxy_net`**

Only after user approval, add `proxy_net` to the `seekarr` service networks:

```yaml
    networks:
      - media_net
      - proxy_net
```

- [ ] **Step 3: Add Homepage entry if exposed**

Add under `Download Management`:

```yaml
    - Seekarr:
        icon: mdi-magnify-scan
        href: https://seekarr.home.lab
        description: Missing media search automation
        siteMonitor: http://seekarr:8788
```


- [ ] **Step 4: Add replacement decision**

Add to `docs/automation/seekarr.md`:

```markdown
## Seekarr vs Mediastarr Decision

- Preferred tool: Seekarr / Mediastarr / neither / both temporarily
- Reason: record observed safety features, maintenance state, UI quality, and dry-run result
- Services to keep installed: record exact services
- Services to remove later: record exact follow-up ticket if any
```

- [ ] **Step 5: Commit exposure/docs changes**

```bash
git add apps/arr-stack/compose.yml apps/utilities/homepage/services.yaml README.md docs/automation/seekarr.md
git commit -m "OPN-247: document Seekarr exposure decision"
```
