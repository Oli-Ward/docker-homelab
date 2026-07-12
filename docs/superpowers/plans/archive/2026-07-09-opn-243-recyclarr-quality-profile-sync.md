# OPN-243 Recyclarr Quality Profile Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Recyclarr to sync selected Sonarr/Radarr quality profiles, custom formats, naming, and TRaSH Guides settings safely.

**Architecture:** Recyclarr belongs in the existing Arr stack because it only needs internal access to Sonarr and Radarr. It must stay off `proxy_net`, have no NPM/AuthentiK exposure, and keep all mutable state under `${APPDATA_ROOT}/recyclarr`.

**Tech Stack:** Docker Compose, Recyclarr `ghcr.io/recyclarr/recyclarr:8`, Sonarr, Radarr, `media_net`, Komodo deployment.

## Global Constraints

- Komodo is the source of truth for deployment; do not run `docker compose up`, `docker compose down`, `docker compose pull`, or restart containers directly without explicit permission.
- Do not commit real `.env` files, Sonarr/Radarr API keys, backup passwords, tokens, cookies, certificates, or runtime state.
- Recyclarr is not a web UI; do not add NPM, AuthentiK, AdGuard DNS, or `proxy_net` exposure.
- Use internal Docker service URLs: `http://sonarr:8989` and `http://radarr:7878`.
- Use major-version image tag `ghcr.io/recyclarr/recyclarr:8`, not `latest`.
- Start with config validation and dry-run/manual sync before enabling scheduled sync.

---

## File Structure

- Modify `apps/arr-stack/compose.yml`: add the `recyclarr` service on `media_net` only.
- Modify `apps/arr-stack/example.env`: document `RECYCLARR_SONARR_API_KEY` and `RECYCLARR_RADARR_API_KEY` placeholders.
- Create `apps/arr-stack/config/recyclarr/recyclarr.yml`: repo-managed starter config using env vars and conservative flags.
- Optionally modify `apps/utilities/homepage/services.yaml`: add a non-UI note only if the user wants a dashboard reminder.
- Modify `README.md`: add Recyclarr to the Management service list and note it is internal-only.

## Sources Checked

- Recyclarr docs: https://recyclarr.dev/
- Recyclarr Docker docs: https://recyclarr.dev/guide/installation/docker/
- Recyclarr GitHub: https://github.com/recyclarr/recyclarr

### Task 1: Add Recyclarr service and env documentation

**Files:**
- Modify: `apps/arr-stack/compose.yml`
- Modify: `apps/arr-stack/example.env`
- Create: `apps/arr-stack/config/recyclarr/recyclarr.yml`

**Interfaces:**
- Consumes: existing `media_net`, `${PUID}`, `${PGID}`, `${TZ}`, `${APPDATA_ROOT}` conventions.
- Produces: `recyclarr` container with `/config` mounted from `${APPDATA_ROOT}/recyclarr` and API keys supplied as environment variables.

- [ ] **Step 1: Add the Compose service**

Insert this service in `apps/arr-stack/compose.yml` near the other Arr automation services, before `networks:`:

```yaml
  # Recyclarr - Sonarr/Radarr quality profile sync
  recyclarr:
    image: ghcr.io/recyclarr/recyclarr:8
    container_name: recyclarr
    user: "${PUID}:${PGID}"
    environment:
      - TZ=${TZ}
      - SONARR_API_KEY=${RECYCLARR_SONARR_API_KEY}
      - RADARR_API_KEY=${RECYCLARR_RADARR_API_KEY}
    volumes:
      - ${APPDATA_ROOT}/recyclarr:/config
    restart: unless-stopped
    networks:
      - media_net
```

- [ ] **Step 2: Document required env vars**

Append to `apps/arr-stack/example.env`:

```env

# Recyclarr API keys for internal Sonarr/Radarr sync
RECYCLARR_SONARR_API_KEY=change-me
RECYCLARR_RADARR_API_KEY=change-me
```

- [ ] **Step 3: Create starter config**

Create `apps/arr-stack/config/recyclarr/recyclarr.yml` with this conservative starter:

```yaml
sonarr:
  tv:
    base_url: http://sonarr:8989
    api_key: !env_var SONARR_API_KEY
    delete_old_custom_formats: false
    replace_existing_custom_formats: false

radarr:
  movies:
    base_url: http://radarr:7878
    api_key: !env_var RADARR_API_KEY
    delete_old_custom_formats: false
    replace_existing_custom_formats: false
```

- [ ] **Step 4: Copy starter config into appdata before Komodo deployment**

Because the Compose mount uses `${APPDATA_ROOT}/recyclarr`, copy the repo starter to the host appdata path during deployment preparation:

```bash
mkdir -p "${APPDATA_ROOT}/recyclarr"
cp apps/arr-stack/config/recyclarr/recyclarr.yml "${APPDATA_ROOT}/recyclarr/recyclarr.yml"
```

Expected: `${APPDATA_ROOT}/recyclarr/recyclarr.yml` exists without containing real API keys.

- [ ] **Step 5: Validate Compose without deploying**

Run from `apps/arr-stack` using safe placeholder values:

```bash
PUID=1000 PGID=1000 TZ=Pacific/Auckland DATA_ROOT=/data APPDATA_ROOT=/srv/appdata RECYCLARR_SONARR_API_KEY=change-me RECYCLARR_RADARR_API_KEY=change-me docker compose config
```

Expected: PASS, rendered config contains `recyclarr`, `media_net`, and no `proxy_net` on the `recyclarr` service.

- [ ] **Step 6: Commit**

```bash
git add apps/arr-stack/compose.yml apps/arr-stack/example.env apps/arr-stack/config/recyclarr/recyclarr.yml
git commit -m "OPN-243: add Recyclarr service config"
```

### Task 2: Roll out safely and document scope

**Files:**
- Modify: `README.md`
- Optional modify: `apps/utilities/homepage/services.yaml`

**Interfaces:**
- Consumes: Recyclarr service from Task 1.
- Produces: documented operational boundary: Recyclarr manages selected profile/custom-format sync only.

- [ ] **Step 1: Update README service catalog**

Add `Recyclarr - Sonarr/Radarr quality profile sync` under the `Management` list in `README.md`.

- [ ] **Step 2: Add internal-only note**

Add this bullet under `README.md` Notes:

```markdown
* Recyclarr is an internal scheduled/CLI service only; do not expose it through Nginx Proxy Manager or Authentik.
```

- [ ] **Step 3: Optional Homepage note**

If the user wants a dashboard reminder, add this under `Download Management` in `apps/utilities/homepage/services.yaml`:

```yaml
    - Recyclarr:
        icon: recyclarr.png
        href: https://recyclarr.dev/
        description: CLI/scheduled profile sync; check container logs
```

If the user does not want non-UI services on Homepage, skip this step and do not edit `services.yaml`.

- [ ] **Step 4: Manual rollout checklist through Komodo**

In Komodo, redeploy the Arr stack after real `.env` keys are present. Do not use direct `docker compose up` unless the user explicitly approves.

Expected after deploy:

```text
recyclarr container exists
recyclarr can resolve sonarr and radarr over media_net
no NPM proxy host exists for recyclarr.home.lab
```

- [ ] **Step 5: First-run commands with explicit permission only**

After deploy, run non-destructive checks inside the container:

```bash
docker logs recyclarr --tail=100
docker exec recyclarr recyclarr config list
docker exec recyclarr recyclarr sync --preview
```

Expected: config loads, Sonarr/Radarr are reachable, and preview shows intended changes before real sync.

- [ ] **Step 6: Commit documentation changes**

```bash
git add README.md apps/utilities/homepage/services.yaml
git commit -m "OPN-243: document Recyclarr rollout boundary"
```
