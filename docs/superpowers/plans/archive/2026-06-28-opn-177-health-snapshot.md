# OPN-177 Health Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable read-only before/after health snapshot pattern for heavy maintenance jobs.

**Architecture:** Implement one shell script that writes a single combined Markdown report under `diagnostics/health/YYYY-MM-DD-<job>.md`. The script captures before and after host health checks around a command, avoids environment output and secrets, and degrades cleanly when Docker, systemd, or journal access is unavailable.

**Tech Stack:** POSIX-ish Bash, Linux read-only host commands, Markdown diagnostics docs.

---

## File Structure

- Create: `diagnostics/health/health-snapshot.sh`
  - Reusable runner for combined before/after snapshots.
  - Accepts a job slug and a command after `--`.
  - Runs read-only checks: timestamp, host identity, uptime, RAM, disk, process memory, Docker stats/ps when available, failed systemd units, recent warning/error journal checks.
  - Writes sections required by OPN-177.
- Modify: `diagnostics/health/README.md`
  - Documents when to use the pattern, safety rules, host support, and example usage.
- Create by verification run: `diagnostics/health/YYYY-MM-DD-opn-177-dummy.md`
  - Harmless dummy-job evidence proving the script works without mutating Docker or services.

## Tasks

### Task 1: Add the Snapshot Script

**Files:**
- Create: `diagnostics/health/health-snapshot.sh`

- [ ] **Step 1: Create the script**

Create an executable Bash script with these functions:

```bash
#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: diagnostics/health/health-snapshot.sh <job-slug> -- <command> [args...]

Writes diagnostics/health/YYYY-MM-DD-<job-slug>.md with Before, Command/job run,
After, Diff / observations, and Recommendation / follow-up sections.
USAGE
}
```

The script should reject missing job slugs, slugs outside `[A-Za-z0-9._-]`, and missing commands. It should create `diagnostics/health`, append command output to the combined report, and use only read-only system commands.

- [ ] **Step 2: Add a reusable check collector**

Add a `collect_health()` function that prints:

```text
date -Iseconds
hostnamectl --static or hostname
systemd-detect-virt
uptime
free -h
df -h
docker stats --no-stream --format ...
docker ps --format ...
ps aux --sort=-%mem | head -n 20
systemctl --failed
journalctl -p warning..alert -n 100 --no-pager
```

Every optional command must be guarded with `command -v` and must write an explanatory line when unavailable. It must not print environment variables, Docker inspect env data, secret files, or full service logs.

- [ ] **Step 3: Add report sections**

The generated file must use exactly this top-level structure:

```markdown
# Health snapshot: <job>

## Before

## Command/job run

## After

## Diff / observations

## Recommendation / follow-up
```

The diff section should include before/after timestamps and tell the reader to compare RAM, disk, process, failed units, Docker status, and warning/error output.

### Task 2: Document Usage

**Files:**
- Modify: `diagnostics/health/README.md`

- [ ] **Step 1: Add a before/after workflow section**

Document that the script should be used for storage migrations, backups, Komodo Docker updates, imports, OpenClaw state map generation, routing evaluations, and Paperless imports/exports.

- [ ] **Step 2: Document safety and support**

State that checks are read-only, secrets and full environment output are intentionally excluded, Docker checks run only when Docker is available, and systemd/journal checks are best effort for both the OpenClaw VM and the media Docker host.

- [ ] **Step 3: Add example commands**

Include:

```bash
diagnostics/health/health-snapshot.sh paperless-export -- paperless-exporter --help
diagnostics/health/health-snapshot.sh opn-177-dummy -- bash -lc 'printf "dummy job\n"; sleep 1'
```

### Task 3: Verify With a Harmless Dummy Job

**Files:**
- Generated: `diagnostics/health/YYYY-MM-DD-opn-177-dummy.md`

- [ ] **Step 1: Run shell syntax validation**

Run:

```bash
bash -n diagnostics/health/health-snapshot.sh
```

Expected: exit 0.

- [ ] **Step 2: Run the dummy job**

Run:

```bash
diagnostics/health/health-snapshot.sh opn-177-dummy -- bash -lc 'printf "dummy job\n"; sleep 1'
```

Expected: exit 0 and a report at `diagnostics/health/YYYY-MM-DD-opn-177-dummy.md`.

- [ ] **Step 3: Check report structure**

Run:

```bash
rg -n '^# Health snapshot: opn-177-dummy|^## Before|^## Command/job run|^## After|^## Diff / observations|^## Recommendation / follow-up|free -h|df -h|ps aux|systemctl --failed|journalctl -p warning..alert' diagnostics/health/YYYY-MM-DD-opn-177-dummy.md
```

Expected: all required headings and command labels appear.

### Task 4: Linear Closeout

**Files:**
- No repo files.

- [ ] **Step 1: Comment on OPN-177**

Comment with:

- Script path.
- README path.
- Dummy report path.
- Verification commands and results.
- Note that no Docker or systemd mutations were performed.

- [ ] **Step 2: Move OPN-177 to Done only after verification passes**

Use Linear status update after the comment and only if the acceptance criteria are met.

## Self-Review

- Spec coverage: The plan creates a reusable script/template, includes all requested health checks, supports OpenClaw/media hosts via best-effort command availability, documents usage, tests a harmless dummy job, and writes the combined report path.
- Placeholder scan: No TBD/TODO/fill-in placeholders.
- Type consistency: Paths and command names are consistent across tasks.
