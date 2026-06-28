# OPN-196-198 Exposure Reviews Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete report-only exposure reviews for Jellyfin, n8n, and gluetun-published downloader admin ports.

**Architecture:** Use repo compose files, existing OPN-190/OPN-175 diagnostics, and targeted read-only Docker metadata as evidence. Write one diagnostics report per issue under `diagnostics/build-lanes/`, then comment and close each Linear issue without applying Docker, firewall, proxy, or compose enforcement changes.

**Tech Stack:** Markdown diagnostics reports, Linear comments, read-only Docker CLI commands.

---

## File Structure

- Create: `diagnostics/build-lanes/2026-06-28-opn-196-jellyfin-exposure-review.md`
  - Documents current Jellyfin exposure model and remediation plan.
- Create: `diagnostics/build-lanes/2026-06-28-opn-197-n8n-exposure-runtime-mounts.md`
  - Documents approved n8n read-only inspection packet, mount/socket result, and exposure recommendation.
- Create: `diagnostics/build-lanes/2026-06-28-opn-198-gluetun-admin-ports.md`
  - Identifies TCP `6789` and TCP `8080` behind gluetun and records admin-surface relevance.

## Tasks

### Task 1: Gather Evidence

**Files:**
- Read: `apps/media/compose.yml`
- Read: `apps/utilities/compose.yml`
- Read: `apps/downloads/compose.yml`
- Read: `diagnostics/build-lanes/2026-06-28-opn-190-live-media-boundary-audit.md`
- Read: `diagnostics/build-lanes/2026-06-28-opn-175-firewall-policy.md`

- [ ] Run read-only Docker inventory:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | rg '^(NAMES|jellyfin|n8n|gluetun|qbittorrent|nzbget)\b'
```

- [ ] Run targeted, non-secret Docker inspect formats for `jellyfin`, `n8n`, `gluetun`, `qbittorrent`, and `nzbget`.

### Task 2: Write Reports

**Files:**
- Create: `diagnostics/build-lanes/2026-06-28-opn-196-jellyfin-exposure-review.md`
- Create: `diagnostics/build-lanes/2026-06-28-opn-197-n8n-exposure-runtime-mounts.md`
- Create: `diagnostics/build-lanes/2026-06-28-opn-198-gluetun-admin-ports.md`

- [ ] OPN-196 report states whether direct Jellyfin host exposure is intended, documents current repo/live state, and gives a safe remediation plan before enforcement.
- [ ] OPN-197 report includes the read-only inspection packet, confirms/disproves Docker socket access, confirms/disproves broad host mounts, and recommends a separate remediation issue if direct `5678` is not justified.
- [ ] OPN-198 report identifies `6789` as NZBGet UI and `8080` as qBittorrent UI through gluetun, and documents OPN-175 firewall policy implications.

### Task 3: Verify And Close Linear

**Files:**
- No additional repo files.

- [ ] Run `rg` checks proving each report contains required decisions and evidence.
- [ ] Run `git status --short` and verify only expected new/modified files are present, apart from pre-existing unrelated files.
- [ ] Comment on OPN-196, OPN-197, and OPN-198 with report paths, evidence commands, and recommendations.
- [ ] Move each issue to Done only after the report covers its acceptance criteria.

## Self-Review

- Spec coverage: The plan covers the three named issues, their explicit acceptance criteria, OPN-175 linkage, and report-only safety constraints.
- Placeholder scan: No TBD/TODO/fill-in placeholders.
- Type consistency: Report paths and issue identifiers match the requested tickets.
