# OPN-190 Live Media Boundary Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a dated, non-secret, report-only live media boundary audit for OPN-190, or block with evidence if the exact approved host command packet is not available.

**Architecture:** This is a documentation and diagnostics task, not a deployment task. The worker must only run explicitly approved read-only checks against named host(s), record summarized non-secret findings, and update Linear. If the approval packet does not name host(s) and allowed commands, the worker must not run live host, Docker, sudo, firewall, or reverse-proxy checks.

**Tech Stack:** Linear, Markdown diagnostics, shell read-only checks, Docker read-only inspection only when explicitly approved.

---

### Task 1: Confirm Approval Gate And Write Audit Report

**Files:**
- Create: `diagnostics/build-lanes/2026-06-28-opn-190-live-media-boundary-audit.md`
- Reference: `docs/superpowers/plans/2026-06-28-opn-190-live-media-boundary-audit.md`

- [ ] **Step 1: Re-read Linear issue and comments**

Run through the Linear connector:

```text
fetch issue:OPN-190
list comments for OPN-190
```

Expected: issue scope confirms report-only live audit and comments either contain an exact approved host command packet or confirm that approval is still missing.

- [ ] **Step 2: Search workspace for approval packet**

Run:

```bash
rg -n "OPN-190|approved command packet|access packet|live media boundary|media boundary audit|gateway verification|ss -tulpn|docker ps --format|sudo ufw" docs diagnostics .github . 2>/dev/null
rg --files docs diagnostics .github . | rg "190|media-boundary|gateway|audit|approval|packet"
```

Expected: either find an exact packet naming host(s), allowed commands, sudo/Docker scope, and redaction requirements, or no packet is present.

- [ ] **Step 3: If and only if exact approval exists, run approved read-only checks**

Only run commands listed in the packet against the named host(s). The issue-suggested command set is:

```bash
ss -tulpn
ip addr
sudo ufw status verbose || true
docker ps --format 'table {{.Names}}\t{{.Ports}}'
```

Expected: collect only summarized non-secret evidence. Redact private IPs, tokens, env values, API keys, secrets, and any sensitive details before writing the report.

- [ ] **Step 4: If approval is missing or incomplete, do not run live checks**

Do not run:

```bash
ss -tulpn
ip addr
sudo ufw status verbose || true
docker ps --format 'table {{.Names}}\t{{.Ports}}'
docker inspect
docker logs
docker compose
firewall commands
reverse-proxy commands
```

Expected: report explicitly states that no live host commands were run because the exact approved packet was unavailable or incomplete.

- [ ] **Step 5: Write the non-secret diagnostics report**

Create `diagnostics/build-lanes/2026-06-28-opn-190-live-media-boundary-audit.md` with these sections:

```markdown
# OPN-190 Live Media Boundary Audit

## Scope

## Approval Packet

## Commands And Categories Run

## Non-Secret Findings

## OpenClaw Gateway Path

## Direct Media/Admin Surface Exposure

## n8n Runtime And Mount Review

## Follow-Up Issues Needed

## OPN-175 Readiness
```

Expected: the report answers whether OpenClaw reaches only the approved gateway path, whether any direct media/admin surfaces are exposed, whether n8n has Docker socket or broad host mounts, follow-up issues needed, and whether OPN-175 can proceed. If live audit was blocked, every unknown remains explicitly unknown.

- [ ] **Step 6: Verify the report is non-secret and scoped**

Run:

```bash
sed -n '1,240p' diagnostics/build-lanes/2026-06-28-opn-190-live-media-boundary-audit.md
rg -n "token|secret|password|api[_-]?key|private key|BEGIN .*KEY|Authorization|Bearer|COOKIE|SESSION|[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" diagnostics/build-lanes/2026-06-28-opn-190-live-media-boundary-audit.md
git diff -- docs/superpowers/plans/2026-06-28-opn-190-live-media-boundary-audit.md diagnostics/build-lanes/2026-06-28-opn-190-live-media-boundary-audit.md
```

Expected: report contains no secrets and no unredacted private IP details; diff only includes the plan and report.

### Task 2: Update Linear

**Files:**
- No local file changes.

- [ ] **Step 1: Comment on OPN-190**

Post a Linear comment with:

```markdown
Outcome: done or blocked.

Commands/categories run:
- ...

Non-secret findings:
- ...

OpenClaw gateway path:
- ...

Direct media/admin surfaces:
- ...

n8n socket/mount review:
- ...

Follow-up issues needed:
- ...

OPN-175 readiness:
- ...

Report: diagnostics/build-lanes/2026-06-28-opn-190-live-media-boundary-audit.md
```

Expected: the comment contains no secrets, env values, tokens, unredacted private IPs, or sensitive operational details.

- [ ] **Step 2: Set Linear status**

If live evidence satisfies the acceptance criteria, move OPN-190 to `Done`. If approval is missing/incomplete or live evidence cannot be collected, move it to `Blocked` and state the exact next action needed.

Expected: Linear status matches the evidence, not the intended outcome.
