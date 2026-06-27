# OPN-157 Homepage Config Repo Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move safe Homepage configuration into this repo while replacing literal widget secrets with `HOMEPAGE_VAR_*` environment references.

**Architecture:** The utilities stack will bind-mount a repo-local Homepage config directory into `/app/config`. The repo will track only selected Homepage config files by whitelist, while the real utilities `.env` remains untracked and carries secret values. Existing live `/data/configs/homepage` files are treated as the source snapshot for the initial sanitized repo copy, but live deployment remains a Komodo redeploy step.

**Tech Stack:** Docker Compose, Homepage YAML config, `.env` variable interpolation, Git ignore rules.

---

## File Structure

- Create: `apps/utilities/homepage/bookmarks.yaml` - safe Homepage bookmarks config copied from live config.
- Create: `apps/utilities/homepage/docker.yaml` - safe Homepage Docker integration config copied from live config.
- Create: `apps/utilities/homepage/kubernetes.yaml` - safe Homepage Kubernetes config copied from live config.
- Create: `apps/utilities/homepage/proxmox.yaml` - safe Homepage Proxmox sample/comment config copied from live config.
- Create: `apps/utilities/homepage/services.yaml` - Homepage services config copied from live config with widget secrets replaced by `{{HOMEPAGE_VAR_*}}` references.
- Create: `apps/utilities/homepage/settings.yaml` - safe Homepage settings config copied from live config.
- Create: `apps/utilities/homepage/widgets.yaml` - safe Homepage widgets config copied from live config.
- Create: `apps/utilities/homepage/custom.css` - safe custom CSS copied from live config if non-secret.
- Create: `apps/utilities/homepage/custom.js` - safe custom JS copied from live config if non-secret.
- Modify: `.gitignore` - ignore all Homepage config files by default, then whitelist approved YAML/CSS/JS files.
- Modify: `apps/utilities/compose.yml` - mount `./homepage:/app/config` for Homepage instead of `${DATA_ROOT}/configs/homepage:/app/config`.
- Modify: `apps/utilities/example.env` - document every `HOMEPAGE_VAR_*` secret required by the sanitized Homepage config.

## Task 1: Prepare Sanitized Homepage Config

**Files:**
- Create: `apps/utilities/homepage/*.yaml`
- Create: `apps/utilities/homepage/custom.css`
- Create: `apps/utilities/homepage/custom.js`

- [ ] **Step 1: Create repo-local Homepage directory**

Run:

```bash
mkdir -p apps/utilities/homepage
```

Expected: directory exists and `git status --short apps/utilities/homepage` shows no tracked changes yet.

- [ ] **Step 2: Copy safe live files into the repo-local Homepage directory with secret values rewritten**

Use a script or careful manual edit to copy the live files from `/data/configs/homepage` into `apps/utilities/homepage`. The copied `services.yaml` must replace sensitive widget values with these exact references:

```yaml
key: "{{HOMEPAGE_VAR_SPEEDTEST_API_KEY}}"
key: "{{HOMEPAGE_VAR_JELLYFIN_API_KEY}}"
password: "{{HOMEPAGE_VAR_QBITTORRENT_PASSWORD}}"
password: "{{HOMEPAGE_VAR_NZBGET_PASSWORD}}"
key: "{{HOMEPAGE_VAR_JELLYSEERR_API_KEY}}"
key: "{{HOMEPAGE_VAR_PROWLARR_API_KEY}}"
key: "{{HOMEPAGE_VAR_RADARR_API_KEY}}"
key: "{{HOMEPAGE_VAR_SONARR_API_KEY}}"
key: "{{HOMEPAGE_VAR_BAZARR_API_KEY}}"
key: "{{HOMEPAGE_VAR_KOMODO_API_KEY}}"
secret: "{{HOMEPAGE_VAR_KOMODO_API_SECRET}}"
key: "{{HOMEPAGE_VAR_TAILSCALE_API_KEY}}"
password: "{{HOMEPAGE_VAR_ADGUARD_PASSWORD}}"
key: "{{HOMEPAGE_VAR_AUTHENTIK_API_KEY}}"
password: "{{HOMEPAGE_VAR_NPM_PASSWORD}}"
X-Api-Key: "{{HOMEPAGE_VAR_CLEANUPARR_API_KEY}}"
```

Expected: the repo-local `services.yaml` preserves the live dashboard structure but contains no literal API keys, tokens, passwords, or secrets.

- [ ] **Step 3: Verify the repo-local Homepage config has no obvious literal secrets**

Run:

```bash
rg -n "key: [A-Za-z0-9_+=/-]{12,}|password: [^\"{][^[:space:]]+|secret: [^\"{][^[:space:]]+|X-Api-Key: [^\"{][^[:space:]]+" apps/utilities/homepage
```

Expected: no matches.

## Task 2: Wire Homepage Compose To Repo Config

**Files:**
- Modify: `apps/utilities/compose.yml`

- [ ] **Step 1: Change the Homepage config mount**

Replace the Homepage config volume:

```yaml
- ${DATA_ROOT}/configs/homepage:/app/config
```

with:

```yaml
- ./homepage:/app/config
```

Expected: only the Homepage `/app/config` mount changes; other utilities stack mounts stay on their current paths.

## Task 3: Document Homepage Secret Variables

**Files:**
- Modify: `apps/utilities/example.env`

- [ ] **Step 1: Add safe placeholders for all Homepage widget secrets**

Add these variables under the existing Homepage section:

```env
HOMEPAGE_VAR_SPEEDTEST_API_KEY=change-me
HOMEPAGE_VAR_JELLYFIN_API_KEY=change-me
HOMEPAGE_VAR_QBITTORRENT_PASSWORD=change-me
HOMEPAGE_VAR_NZBGET_PASSWORD=change-me
HOMEPAGE_VAR_JELLYSEERR_API_KEY=change-me
HOMEPAGE_VAR_PROWLARR_API_KEY=change-me
HOMEPAGE_VAR_RADARR_API_KEY=change-me
HOMEPAGE_VAR_SONARR_API_KEY=change-me
HOMEPAGE_VAR_BAZARR_API_KEY=change-me
HOMEPAGE_VAR_KOMODO_API_KEY=change-me
HOMEPAGE_VAR_KOMODO_API_SECRET=change-me
HOMEPAGE_VAR_TAILSCALE_API_KEY=change-me
HOMEPAGE_VAR_ADGUARD_PASSWORD=change-me
HOMEPAGE_VAR_AUTHENTIK_API_KEY=change-me
HOMEPAGE_VAR_NPM_PASSWORD=change-me
HOMEPAGE_VAR_CLEANUPARR_API_KEY=change-me
```

Expected: `apps/utilities/example.env` documents every `HOMEPAGE_VAR_*` variable referenced by `apps/utilities/homepage/services.yaml`.

## Task 4: Add Git Whitelist

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Ignore unapproved Homepage config files by default**

Add this block near the existing general ignore rules:

```gitignore
# Homepage repo-managed config whitelist
apps/utilities/homepage/*
!apps/utilities/homepage/*.yaml
!apps/utilities/homepage/custom.css
!apps/utilities/homepage/custom.js
```

Expected: `apps/utilities/homepage/logs/`, generated files, and unknown files remain ignored unless explicitly whitelisted later.

## Task 5: Validate And Handoff

**Files:**
- Check: `.gitignore`
- Check: `apps/utilities/compose.yml`
- Check: `apps/utilities/example.env`
- Check: `apps/utilities/homepage/*`

- [ ] **Step 1: Confirm every Homepage env reference has an example variable**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
import re
refs = set(re.findall(r'HOMEPAGE_VAR_[A-Z0-9_]+', Path('apps/utilities/homepage/services.yaml').read_text()))
envs = set()
for line in Path('apps/utilities/example.env').read_text().splitlines():
    if line.startswith('HOMEPAGE_VAR_') and '=' in line:
        envs.add(line.split('=', 1)[0])
missing = sorted(refs - envs)
extra = sorted(envs - refs - {'HOMEPAGE_VAR_TITLE'})
print('missing:', missing)
print('extra:', extra)
raise SystemExit(1 if missing else 0)
PY
```

Expected: `missing: []`.

- [ ] **Step 2: Validate the utilities compose file with placeholder environment values**

Run:

```bash
env $(grep -v '^#' apps/utilities/example.env | xargs) docker compose -f apps/utilities/compose.yml config >/tmp/opn-157-utilities-compose.yml
```

Expected: command exits 0 and writes `/tmp/opn-157-utilities-compose.yml`.

- [ ] **Step 3: Check for accidental committed secret patterns**

Run:

```bash
rg -n "password: [^\"{][^[:space:]]+|secret: [^\"{][^[:space:]]+|key: [A-Za-z0-9_+=/-]{12,}|X-Api-Key: [^\"{][^[:space:]]+" apps/utilities/homepage apps/utilities/example.env
```

Expected: no matches except safe placeholder values if the pattern is too broad. Any real secret match must be removed before handoff.

- [ ] **Step 4: Review Git status**

Run:

```bash
git status --short
```

Expected: changes are limited to the Homepage config refactor, the plan/spec docs, and any pre-existing unrelated untracked files.

- [ ] **Step 5: Prepare handoff**

Document that the operator must copy real secret values into `apps/utilities/.env` and redeploy the utilities stack through Komodo. Do not run `docker compose up`, restart Homepage, or mutate live Docker state.
