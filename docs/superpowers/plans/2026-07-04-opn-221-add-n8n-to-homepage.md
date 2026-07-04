# OPN-221 Add n8n To Homepage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add n8n to the repo-managed Homepage dashboard with a working link and internal status check.

**Architecture:** Homepage remains configured from the tracked `apps/utilities/homepage` directory. n8n already runs in `apps/utilities/compose.yml` on `utilities_net` and `proxy_net`, so the dashboard card should link users through the reverse-proxied `https://n8n.home.lab` URL while monitoring the Docker-internal `http://n8n:5678` endpoint. No n8n credentials or API keys are introduced.

**Tech Stack:** Docker Compose, Homepage YAML configuration, Nginx Proxy Manager route expectation, Linear OPN-221.

---

### Task 1: Add Homepage n8n Service Card

**Files:**
- Modify: `apps/utilities/homepage/services.yaml`
- Modify: `apps/utilities/homepage/settings.yaml`

- [x] **Step 1: Add an Automation group with n8n**

Insert this section in `apps/utilities/homepage/services.yaml` after the `Download Management` section and before `System`:

```yaml
# Automation
- Automation:
    - n8n:
        icon: n8n.png
        href: https://n8n.home.lab
        description: Workflow Automation
        siteMonitor: http://n8n:5678
```

- [x] **Step 2: Add Automation layout settings**

Insert this block in `apps/utilities/homepage/settings.yaml` after `Download Management` and before `System`:

```yaml
  Automation:
    style: row
    columns: 4
    icon: mdi-robot
```

- [x] **Step 3: Validate YAML syntax**

Run:

```bash
python - <<'PY'
from pathlib import Path
import yaml

for path in [
    Path("apps/utilities/homepage/services.yaml"),
    Path("apps/utilities/homepage/settings.yaml"),
]:
    yaml.safe_load(path.read_text())
    print(f"ok {path}")
PY
```

Expected: both files print `ok ...` with exit code 0.

### Task 2: Document Dashboard Inventory

**Files:**
- Modify: `README.md`

- [x] **Step 1: Add n8n to the Utilities service list**

In `README.md`, add this bullet under `### Utilities`:

```markdown
* n8n – Workflow automation
```

- [x] **Step 2: Add n8n to domain examples**

In `README.md`, add this bullet under the `Examples:` list:

```markdown
* `n8n.home.lab`
```

### Task 3: Validate Compose And Diff

**Files:**
- Check: `apps/utilities/compose.yml`
- Check: `apps/utilities/homepage/services.yaml`
- Check: `apps/utilities/homepage/settings.yaml`
- Check: `README.md`

- [x] **Step 1: Render the utilities Compose config with example-safe values**

Run:

```bash
PUID=1000 PGID=1000 TZ=Pacific/Auckland DATA_ROOT=/data APPDATA_ROOT=/srv/appdata HOMEPAGE_ALLOWED_HOSTS=dash.home.lab HOMEPAGE_VAR_TITLE=Homelab HOMEPAGE_VAR_SPEEDTEST_API_KEY=change-me HOMEPAGE_VAR_JELLYFIN_API_KEY=change-me HOMEPAGE_VAR_QBITTORRENT_PASSWORD=change-me HOMEPAGE_VAR_NZBGET_PASSWORD=change-me HOMEPAGE_VAR_JELLYSEERR_API_KEY=change-me HOMEPAGE_VAR_PROWLARR_API_KEY=change-me HOMEPAGE_VAR_RADARR_API_KEY=change-me HOMEPAGE_VAR_SONARR_API_KEY=change-me HOMEPAGE_VAR_BAZARR_API_KEY=change-me HOMEPAGE_VAR_KOMODO_API_KEY=change-me HOMEPAGE_VAR_KOMODO_API_SECRET=change-me HOMEPAGE_VAR_TAILSCALE_API_KEY=change-me HOMEPAGE_VAR_ADGUARD_PASSWORD=change-me HOMEPAGE_VAR_AUTHENTIK_API_KEY=change-me HOMEPAGE_VAR_NPM_PASSWORD=change-me HOMEPAGE_VAR_CLEANUPARR_API_KEY=change-me HOMEPAGE_VAR_PAPERLESS_PASSWORD=change-me ICLOUD_USERNAME=example@icloud.com SPEEDTEST_KEY=example-speedtest-key SPEEDTEST_APP_URL=https://speedtest.home.lab N8N_PORT=5678 N8N_SECURE_COOKIE=false NODES_EXCLUDE=[] OPENCLAW_SSH_HOST=192.0.2.16 OPENCLAW_SSH_USER=openclaw OPENCLAW_SSH_PORT=22 OPENCLAW_SSH_KEY_PATH_HOST=/home/oli/.ssh/openclaw/openclaw_lab_tunnel OPENCLAW_SSH_KEY_PATH=/home/node/.n8n/ssh/openclaw_lab_tunnel OPENCLAW_WORKSPACE=/home/openclaw/.openclaw/workspace OPENCLAW_RATING_PROMPT_DB=tracking/jellyfin-rating-prompts/rating-prompts.sqlite docker compose -f apps/utilities/compose.yml --env-file apps/utilities/example.env config >/tmp/opn-221-utilities-compose.yml
```

Expected: exit code 0. Do not run `docker compose up`, `down`, `pull`, or restart containers.

- [x] **Step 2: Review the scoped diff**

Run:

```bash
git diff -- apps/utilities/homepage/services.yaml apps/utilities/homepage/settings.yaml README.md docs/superpowers/plans/2026-07-04-opn-221-add-n8n-to-homepage.md
```

Expected: only the n8n Homepage card, Automation layout, README inventory/domain bullets, and this plan file changed.

### Task 4: Linear Handoff

**Files:**
- Check: Git diff and verification output

- [x] **Step 1: Move OPN-221 through review/done only after verification**

After validation passes, add a Linear comment with:

```markdown
Outcome: done

Changed:
- Added n8n to Homepage under Automation.
- Linked to https://n8n.home.lab and used internal siteMonitor http://n8n:5678.
- Documented n8n in the README service/domain inventory.

Verification:
- YAML parse check for Homepage services/settings passed.
- docker compose config for apps/utilities/compose.yml passed with example-safe env values.

Commit/PR: none unless requested.

Follow-ups:
- Komodo redeploy of the utilities stack.
- Confirm NPM/DNS/Auth route for https://n8n.home.lab if not already live.
```

Then move OPN-221 to `Done` only if the verification commands passed.
