# OPN-194 Komodo Media Stack Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a read-only, documentation-only audit of current Komodo-managed media stacks, current manual update workflow evidence, and how observed services map to the `OPN-173` update policy buckets.

**Architecture:** The audit will combine repository evidence, read-only Docker metadata, and any available read-only Komodo UI/API evidence without triggering updates, redeploys, pulls, or config changes. If approved access cannot prove the manual Komodo click-path or Komodo-managed inventory directly, the report will name the exact unknowns and distinguish Docker/Compose evidence from Komodo evidence.

**Tech Stack:** Docker Compose metadata, Komodo, Linear, Markdown diagnostics.

---

### Task 1: Capture Current Evidence Baseline

**Files:**
- Create: `diagnostics/komodo/2026-06-28-opn-194-komodo-media-stack-audit.md`
- Modify: `docs/superpowers/plans/2026-06-28-opn-194-komodo-media-stack-audit.md`

- [x] **Step 1: Record non-secret repo and Docker metadata commands**

Run these read-only commands from `/home/oli/docker`:

```bash
git status --short --branch
git ls-files '*compose*.yml' '*compose*.yaml'
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Labels}}'
docker ps --format '{{.Names}}' | while IFS= read -r c; do docker inspect "$c" --format '{{.Name}}|{{index .Config.Labels "com.docker.compose.project"}}|{{index .Config.Labels "com.docker.compose.project.config_files"}}|{{index .Config.Labels "com.docker.compose.project.environment_file"}}|{{index .Config.Labels "com.docker.compose.project.working_dir"}}|{{index .Config.Labels "com.centurylinklabs.watchtower.enable"}}'; done
docker network ls --format '{{.Name}}'
```

Expected: commands exit 0 and print metadata only. Do not run `docker compose`, `docker exec`, `docker pull`, `docker restart`, `docker update`, or any Komodo mutation.

- [x] **Step 2: Read compose files without secrets**

Run:

```bash
sed -n '1,260p' apps/media/compose.yml
sed -n '1,320p' apps/arr-stack/compose.yml
sed -n '1,320p' apps/downloads/compose.yml
sed -n '1,260p' apps/docs/compose.yml
sed -n '1,240p' apps/utilities/compose.yml
sed -n '1,220p' apps/openclaw-gateway/compose.yml
sed -n '1,260p' identity/authentik/compose.yml
sed -n '1,220p' infra/proxy/nginx-proxy-manager/compose.yml
sed -n '1,220p' infra/dns/adguard/compose.yml
sed -n '1,220p' platform/komodo/mongo.compose.yaml
```

Expected: tracked YAML content only. Do not open real `.env` or `compose.env` files.

### Task 2: Inspect Read-Only Komodo Workflow Evidence

**Files:**
- Modify: `diagnostics/komodo/2026-06-28-opn-194-komodo-media-stack-audit.md`

- [x] **Step 1: Search repo-managed docs and dashboard config for Komodo links and workflow references**

Run:

```bash
rg -n --hidden -g '!*.env' -g '!**/.env' -g '!platform/komodo/compose.env' -g '!**/.git/**' 'Komodo|update|redeploy|procedure|procedure|stack|manual' README.md AGENTS.md apps docs diagnostics platform infra identity
sed -n '130,190p' apps/utilities/homepage/services.yaml
```

Expected: documentation references and dashboard service labels only.

- [x] **Step 2: Attempt read-only Komodo UI/API evidence only if already accessible without secrets**

Use a browser or unauthenticated metadata endpoint only if it is already available in the current session. Do not read token files, scrape passwords, change settings, click update/redeploy controls, or start procedures.

Expected: either captured read-only evidence of stack list/update UI labels, or a documented unknown explaining why the current approved access did not prove the exact click-path.

### Task 3: Write The Audit Report

**Files:**
- Create: `diagnostics/komodo/2026-06-28-opn-194-komodo-media-stack-audit.md`
- Modify: `docs/superpowers/plans/2026-06-28-opn-194-komodo-media-stack-audit.md`

- [x] **Step 1: Create the report**

Write a Markdown report with these sections:

```markdown
# OPN-194 Komodo Media Stack Inventory And Manual Update Audit

## Scope And Safety

## Evidence Summary

## Observed Compose And Docker Inventory

## Komodo-Managed Inventory Evidence

## OPN-173 Policy Bucket Mapping

## Manual Komodo Update Workflow Evidence

## Update Indicators, Tags, Procedures, And Batch Rollout Evidence

## Unknowns

## Safety Notes

## Verification Commands
```

Expected: report contains no secrets, raw host-private details beyond repo-local paths already present in prior diagnostics, `.env` values, tokens, cookies, or raw inspect dumps.

- [x] **Step 2: Mark checklist items completed in this plan as evidence is captured**

Update each completed checkbox in `docs/superpowers/plans/2026-06-28-opn-194-komodo-media-stack-audit.md` from `[ ]` to `[x]`.

### Task 4: Verify And Finish Linear

**Files:**
- Modify: `docs/superpowers/plans/2026-06-28-opn-194-komodo-media-stack-audit.md`

- [x] **Step 1: Verify documentation-only output**

Run:

```bash
git diff -- docs/superpowers/plans/2026-06-28-opn-194-komodo-media-stack-audit.md diagnostics/komodo/2026-06-28-opn-194-komodo-media-stack-audit.md
git diff --check -- docs/superpowers/plans/2026-06-28-opn-194-komodo-media-stack-audit.md diagnostics/komodo/2026-06-28-opn-194-komodo-media-stack-audit.md
rg -n 'password|token|secret|api[_-]?key|cookie|authorization|PRIVATE KEY' diagnostics/komodo/2026-06-28-opn-194-komodo-media-stack-audit.md docs/superpowers/plans/2026-06-28-opn-194-komodo-media-stack-audit.md
```

Expected: only documentation files are changed for this issue, `git diff --check` exits 0, and the secret scan finds no real secret values. Policy text that names secret classes is acceptable.

- [x] **Step 2: Update Linear**

Move `OPN-194` to `Done` only if the acceptance criteria are satisfied. Add a final comment containing outcome, changed files, verification commands/results, commit hash if any, and remaining unknowns.
