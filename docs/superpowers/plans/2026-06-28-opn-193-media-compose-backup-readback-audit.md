# OPN-193 Media Compose Backup Readback Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a documentation-only, read-only audit of the live media Docker compose repo and current backup/readback setup for `OPN-193`.

**Architecture:** This is an evidence capture task, not a code change. Read repo metadata, ignore rules, compose file layout, and backup/readback references, then write a dated audit report under `diagnostics/backup/` without printing or copying secret values.

**Tech Stack:** Git, Docker Compose YAML files, shell read-only inspection commands, Markdown documentation.

---

### Task 1: Capture Compose Repo And Git Exclusion Evidence

**Files:**
- Create: `diagnostics/backup/2026-06-28-opn-193-media-compose-backup-readback-audit.md`
- Read only: `.gitignore`
- Read only: `apps/**/compose.yml`
- Read only: `infra/**/compose.yml`
- Read only: `identity/**/compose.yml`
- Read only: `platform/**/compose*.yaml`

- [ ] **Step 1: Inspect repository status and tracked compose files**

Run:

```bash
git status --short
git ls-files '*compose*.yml' '*compose*.yaml'
```

Expected: output lists current worktree changes and all Git-tracked compose files without mutating the repo.

- [ ] **Step 2: Inspect ignore rules without reading real env files**

Run:

```bash
sed -n '1,220p' .gitignore
git ls-files '*.env' '.env' '**/.env'
git ls-files '*example.env' '*.env.example'
```

Expected: `.env`/secret-bearing rules are visible, real secret files are not printed, and example env files are listed if tracked.

- [ ] **Step 3: Check whether real env files are ignored by Git**

Run:

```bash
git status --ignored --short -- ':*.env' ':**/.env' ':**/*.env'
```

Expected: ignored env paths, if present, are shown by path only. Do not open or print their contents.

### Task 2: Capture Backup And Readback Evidence

**Files:**
- Create: `diagnostics/backup/2026-06-28-opn-193-media-compose-backup-readback-audit.md`
- Read only: `README.md`
- Read only: `AGENTS.md`
- Read only: `CLAUDE.md`
- Read only: `docs/**/*.md`
- Read only: `Taskfile.yml`

- [ ] **Step 1: Search repo documentation for backup and restore references**

Run:

```bash
rg -n --hidden -g '!*.env' -g '!**/.env' -g '!**/.git/**' '(backup|restore|readback|restic|borg|rsync|snapshot|appdata|APPDATA_ROOT|DATA_ROOT|Komodo)' .
```

Expected: documentation and config references are captured without secret file contents.

- [ ] **Step 2: Inspect live Docker state read-only if useful for current compose locations**

Run:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Labels}}'
```

Expected: current containers and labels are visible. Do not stop, restart, pull, or recreate anything.

- [ ] **Step 3: Inspect relevant container labels read-only if compose project paths are not clear from repo evidence**

Run this only for specific containers where the label table indicates Compose metadata is useful:

```bash
docker inspect <container-name> --format '{{json .Config.Labels}}'
```

Expected: Compose labels may show project/config file paths. Do not include secret values in the report.

### Task 3: Write Audit Report And Verify Documentation-Only Output

**Files:**
- Create: `diagnostics/backup/2026-06-28-opn-193-media-compose-backup-readback-audit.md`

- [ ] **Step 1: Write the report**

Create `diagnostics/backup/2026-06-28-opn-193-media-compose-backup-readback-audit.md` with these sections:

```markdown
# OPN-193 Media Compose Backup Readback Audit

## Scope

## Evidence Summary

## Compose Repo And Stack Locations

## Git Tracking And Secret Exclusions

## Backup And Readback Evidence

## Unknowns

## Safety Notes

## Verification Commands
```

- [ ] **Step 2: Verify no secret-bearing files were added**

Run:

```bash
git diff --stat
git diff --name-only
```

Expected: only the plan and audit report files are added for `OPN-193`; no `.env`, key, certificate, database, log, or runtime state files are added.

- [ ] **Step 3: Prepare final Linear update**

Comment on `OPN-193` with:

```markdown
Outcome: done

What changed:
- Added a documentation-only read-only audit report at `diagnostics/backup/2026-06-28-opn-193-media-compose-backup-readback-audit.md`.
- Captured compose repo path, Git tracking/exclusion evidence, and current backup/readback evidence or explicit unknowns.

Verification:
- `git diff --stat`
- `git diff --name-only`
- Read-only shell/Docker inspection commands listed in the report.

Commit: not committed
Branch/PR: none
Remaining follow-ups: None, unless the unknowns section identifies access that still needs external confirmation.
```

