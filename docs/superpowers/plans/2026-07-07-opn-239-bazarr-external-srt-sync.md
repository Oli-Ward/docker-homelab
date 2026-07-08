# OPN-239 Bazarr External SRT Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Document and configure the Bazarr workflow that makes Jellyfin prefer synced external SRT subtitles for movies and TV.

**Architecture:** Bazarr runtime settings are appdata/UI state, not Compose state in this repository. The repo-managed automation is a disabled-by-default `bazarr-sync` helper service under the arr stack's `manual` Compose profile; Komodo is the intended trigger surface, and Homepage links operators to Komodo.

**Tech Stack:** Docker Compose, Bazarr, Sonarr, Radarr, Jellyfin, Markdown, Linear.

## Global Constraints

- Do not run `docker compose up`, `docker compose down`, `docker compose pull`, or restart containers directly.
- Do not mutate live Docker, Komodo, NPM, Authentik, AdGuard, Jellyfin, or Bazarr state without explicit operator approval.
- Do not read or commit `.env` files, API keys, cookies, session files, databases, or app runtime state.
- Treat `${APPDATA_ROOT}/bazarr` as mutable app state outside repo management.
- Existing media paths must remain `${DATA_ROOT}/media/tv` and `${DATA_ROOT}/media/movies`.
- Bazarr is already present in `apps/arr-stack/compose.yml`; do not add a duplicate service.
- The `bazarr-sync` API token must be supplied through untracked `apps/arr-stack/.env`; do not commit real token values.

---

### Task 1: Confirm Repository Boundary

**Files:**
- Read: `apps/arr-stack/compose.yml`
- Read: `README.md`
- Create: `diagnostics/build-lanes/2026-07-07-opn-239-bazarr-external-srt-sync.md`

**Interfaces:**
- Consumes: Linear `OPN-239` scope and current repo compose layout.
- Produces: A durable runbook that an operator can apply in Bazarr and Jellyfin.

- [ ] **Step 1: Confirm Bazarr already mounts movie and TV media paths**

Run:

```bash
sed -n '45,70p' apps/arr-stack/compose.yml
```

Expected: Bazarr has `/config`, `/tv`, and `/movies` mounts using `${APPDATA_ROOT}` and `${DATA_ROOT}`.

- [ ] **Step 2: Confirm there is no repo-managed Bazarr runtime config**

Run:

```bash
rg -n "Bazarr|bazarr|subtitle|SRT|srt" . -g '!*.env' -g '!**/.git/**'
```

Expected: only compose, Homepage, backup, and previous diagnostic references appear. There is no committed Bazarr settings file to edit.

- [ ] **Step 3: Write the runbook**

Create `diagnostics/build-lanes/2026-07-07-opn-239-bazarr-external-srt-sync.md` with the exact settings and verification procedure from Task 2.

### Task 2: Document The Bazarr And Jellyfin Workflow

**Files:**
- Modify: `diagnostics/build-lanes/2026-07-07-opn-239-bazarr-external-srt-sync.md`

**Interfaces:**
- Consumes: Official Bazarr settings terminology and OPN-239 acceptance criteria.
- Produces: Operator-ready configuration and cleanup instructions.

- [ ] **Step 1: Record Bazarr future-download settings**

Document these Bazarr UI settings:

```text
Settings -> Subtitles:
- Automatic Subtitles Synchronization: enabled
- Series Score Threshold: enabled, 96
- Movies Score Threshold: enabled, 86

Settings -> Languages / Profiles:
- English profile includes normal external subtitles.
- Do not rely on embedded subtitles as sufficient when the goal is cleaner external SRT.
- Apply the English subtitle profile to monitored Sonarr series and Radarr movies.
```

- [ ] **Step 2: Record Jellyfin verification settings**

Document this Jellyfin-side verification:

```text
1. Scan the relevant Jellyfin library after Bazarr writes subtitles.
2. Open a known affected item on the Google 4K Streamer.
3. Select the track shown as English - SRT - External, or the closest Jellyfin label for an external English SRT file.
4. Confirm the file direct-plays without forcing subtitle burn-in as the default.
```

- [ ] **Step 3: Record existing-library cleanup options**

Document this decision path:

```text
Preferred first pass:
- Use Bazarr UI actions to search/download missing external English SRT subtitles for affected movies and series.
- Use any available Bazarr per-series or per-item synchronization action for existing subtitles.

If bulk synchronization is not available or is too manual:
- Evaluate `bazarr-sync` as a one-off helper using the Bazarr API.
- Do not store the Bazarr API key in the repo.
- Run it from an operator shell with a temporary environment variable.
- Start with a small affected sample before scanning the whole library.
```

### Task 3: Verify The Repo Change

**Files:**
- Check: `diagnostics/build-lanes/2026-07-07-opn-239-bazarr-external-srt-sync.md`
- Check: `docs/superpowers/plans/2026-07-07-opn-239-bazarr-external-srt-sync.md`
- Check: `apps/arr-stack/compose.yml`
- Check: `apps/arr-stack/example.env`
- Check: `apps/utilities/homepage/services.yaml`

**Interfaces:**
- Consumes: Markdown files from Tasks 1 and 2.
- Produces: Validation evidence for Linear final update.

- [ ] **Step 1: Check for accidental secrets**

Run:

```bash
rg -n "token|secret|password|api[_-]?key|cookie|authorization|privkey|BEGIN " diagnostics/build-lanes/2026-07-07-opn-239-bazarr-external-srt-sync.md docs/superpowers/plans/2026-07-07-opn-239-bazarr-external-srt-sync.md apps/arr-stack/compose.yml apps/arr-stack/example.env apps/utilities/homepage/services.yaml
```

Expected: no secret values. Generic references such as `API key` are acceptable if they contain no value.

- [ ] **Step 2: Validate Markdown links and changed files**

Run:

```bash
git diff --check
env PUID=1000 PGID=1000 TZ=Pacific/Auckland DATA_ROOT=/data APPDATA_ROOT=/srv/appdata BAZARR_SYNC_API_TOKEN=change-me docker compose -f apps/arr-stack/compose.yml --profile manual config
git diff -- docs/superpowers/plans/2026-07-07-opn-239-bazarr-external-srt-sync.md diagnostics/build-lanes/2026-07-07-opn-239-bazarr-external-srt-sync.md
```

Expected: `git diff --check` reports no whitespace errors, Compose renders with the manual profile, and the diff contains only the OPN-239 changes.

### Task 4: Update Linear

**Files:**
- Update: Linear `OPN-239`

**Interfaces:**
- Consumes: Verification result from Task 3.
- Produces: A Linear update with what changed and what remains manual.

- [ ] **Step 1: Add final Linear comment**

Add a comment to `OPN-239`:

```markdown
Outcome: repo-side workflow documented and one-off helper added; live Bazarr/Jellyfin verification remains.

What changed:
- Added a Bazarr/Jellyfin runbook for external English SRT downloads, automatic sync thresholds, Jellyfin playback verification, and existing-library cleanup.
- Added a disabled-by-default `bazarr-sync` one-off helper under the arr stack `manual` profile.
- Added a Homepage shortcut to Komodo for triggering the helper.
- Added `BAZARR_SYNC_URL` and `BAZARR_SYNC_API_TOKEN` to `apps/arr-stack/example.env` with safe values/placeholders only.

Verification:
- `git diff --check`
- `docker compose --profile manual config` with placeholder env values
- secret scan against the new plan and runbook

Remaining follow-ups:
- Set `BAZARR_SYNC_API_TOKEN` in the untracked arr-stack `.env`.
- Keep `BAZARR_SYNC_URL=http://bazarr:6767` unless the helper needs to target a different Bazarr instance.
- Trigger `bazarr-sync` from Komodo only when a one-off bulk sync pass is needed.
- Run a Jellyfin library scan and test `English - SRT - External` on the Google 4K Streamer.
```

- [ ] **Step 2: Move Linear to In Review**

Move `OPN-239` to `In Review` after the repo-side verification commands pass. Do not move it to `Done` until the live Bazarr settings and Jellyfin playback acceptance criteria have been applied and verified.
