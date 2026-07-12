# OPN-235 OpenClaw Internal Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the OpenClaw-side internal handoff that lets n8n deliver validated Linear pickup events into OpenClaw without exposing OpenClaw publicly.

**Architecture:** n8n remains the public Linear webhook ingress in the media-host Docker repo. OpenClaw should expose only an internal command that n8n can call over SSH, accepting a normalized JSON payload, validating the Openclaw team and `agent:ready` gate, appending one durable queue event, suppressing duplicates, and emitting a secret-free notification/pickup decision.

**Tech Stack:** OpenClaw workspace scripts, Python queue/validation code, JSONL durable queue, shell wrapper, existing OpenClaw notification/autopickup commands, Linear issue workflow.

---

## Cross-Host Design

The approved design is captured in `docs/superpowers/specs/2026-07-05-linear-openclaw-n8n-handoff-design.md`.

OPN-234 owns the Docker/media-host n8n workflow, real Linear signature verification, and SSH helper. OPN-235 owns the OpenClaw-side command behind that SSH call.

Preferred OpenClaw command contract:

```bash
tools/bin/openclaw-linear-n8n-handoff --event-file <payload-json>
```

The command should read the normalized payload produced by the n8n verifier, re-check the safety gates, append exactly once to the pickup queue, and return machine-readable JSON for `accepted`, `duplicate`, `suppressed`, or `rejected`.

## Workspace Access Note

The local Docker repository is not the implementation target for the OpenClaw command. Read-only inspection from this session found the media-host n8n and gateway configuration, but not the OpenClaw source checkout through the available `oli` account.

Reachability checked on 2026-07-05:

- Linear `OPN-235` is `In Progress`.
- SSH to `oli@192.168.1.16` with `/home/oli/.ssh/openclaw/openclaw_lab_tunnel` reaches host `openclaw-lab`.
- Expected workspace `/home/openclaw/.openclaw/workspace` is missing or inaccessible from the available account.
- `/home/oli/.openclaw` exists but appears to contain runtime state, logs, memory, sessions, and agent state rather than source code; it should not be used as the implementation target.
- Directory search under `/home`, `/opt`, and `/srv` did not find `openclaw_linear_pickup_webhook.py`, `openclaw_linear_autopickup.py`, `openclaw-linear-autopickup`, or `openclaw-notify`.
- `/home/openclaw` is owned by `openclaw:openclaw` with mode `750`, so the available `oli` SSH account cannot inspect it without an explicit privilege/escalation decision.

Do not implement the OpenClaw command in `/home/oli/docker`; that repo should only carry the n8n workflow and helper scripts for OPN-234.

## File Map

- Check: OpenClaw source workspace path to be provided or mounted.
- Modify: `tools/scripts/openclaw_linear_pickup_webhook.py`
  - Reuse existing `PickupCandidate` validation and append semantics if this file exists in the OpenClaw checkout.
- Modify or create: `tools/scripts/openclaw_linear_n8n_handoff.py`
  - Accept normalized JSON from stdin or an event file, validate the minimal n8n payload, enforce gates, append once, and return secret-free machine-readable status.
- Modify or create: `tools/bin/openclaw-linear-n8n-handoff`
  - Stable command wrapper for n8n SSH/Execute Command integration.
- Modify: `tools/scripts/openclaw_linear_autopickup.py`
  - Wire or document the notification decision path for qualifying smoke tickets without bypassing existing approval gates.
- Modify: `tests/` in the OpenClaw checkout
  - Add replay/unit coverage for create/update events, invalid payload shape, duplicate suppression, non-qualifying suppression, and notification decision behavior.
- Check: `tracking/linear-pickup-events/pending.jsonl`
  - Use only as runtime queue state in tests with temporary paths or fixtures; do not commit runtime queue contents.

### Task 1: Resolve Workspace Access

**Files:**
- Check: Linear `OPN-235`
- Check: OpenClaw source checkout

- [x] **Step 1: Read the Linear issue**

Fetched `OPN-235` and confirmed the acceptance criteria require an OpenClaw-side handoff, exact-once queueing, duplicate suppression, notification behavior, and an `OPN-225` update.

- [x] **Step 2: Inspect local repository target**

Run from `/home/oli/docker`:

```bash
rg --files -g 'openclaw*' -g '*linear*' -g '*pickup*' -g 'AGENTS.md' -g 'README.md'
```

Observed: this repository contains the media-host Docker Compose setup, n8n workflow support, and OpenClaw gateway code, but not the OpenClaw workspace scripts named in Linear.

- [x] **Step 3: Check reachable OpenClaw host**

Run:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=5 -i /home/oli/.ssh/openclaw/openclaw_lab_tunnel oli@192.168.1.16 'hostname'
```

Observed: SSH reaches `openclaw-lab`.

- [x] **Step 4: Check expected workspace path**

Run:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=5 -i /home/oli/.ssh/openclaw/openclaw_lab_tunnel oli@192.168.1.16 'test -d /home/openclaw/.openclaw/workspace && echo WORKSPACE_OK || echo WORKSPACE_MISSING'
```

Observed: `WORKSPACE_MISSING`.

- [x] **Step 5: Search for the named OpenClaw scripts**

Run:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=5 -i /home/oli/.ssh/openclaw/openclaw_lab_tunnel oli@192.168.1.16 'find /home /opt /srv -path "*/logs" -prune -o -path "*/sessions" -prune -o -type f \( -name openclaw_linear_pickup_webhook.py -o -name openclaw_linear_autopickup.py -o -name openclaw-linear-autopickup -o -name openclaw-notify \) -print 2>/dev/null'
```

Observed: no matching files visible to the available account.

- [ ] **Step 6: Unblock implementation access**

Provide one of:

```text
1. The correct OpenClaw source checkout path visible to the available account.
2. A mounted/local checkout of the OpenClaw repository.
3. Explicit permission and credentials/command path for safe privileged read/write access to the OpenClaw source checkout.
```

Expected: the worker can run `git status --short --branch` in the OpenClaw source checkout and inspect the scripts named in the Linear comment without reading secrets, logs, sessions, database files, or `.env` files.

### Task 2: Implement The Internal Handoff After Access Is Restored

**Files:**
- Modify or create: OpenClaw `tools/scripts/openclaw_linear_n8n_handoff.py`
- Modify or create: OpenClaw `tools/bin/openclaw-linear-n8n-handoff`
- Modify: OpenClaw queue/autopickup tests

- [ ] **Step 1: Write failing payload validation tests**

Add tests that feed a normalized n8n payload with at least:

```json
{
  "event_id": "linear-opn-235-smoke-1",
  "event_type": "Issue",
  "action": "create",
  "issue": {
    "identifier": "OPN-SMOKE",
    "title": "Smoke pickup",
    "url": "https://linear.app/example/issue/OPN-SMOKE/smoke-pickup",
    "team_key": "OPN",
    "team_name": "Openclaw",
    "labels": ["agent:ready"],
    "priority": "Medium"
  }
}
```

Expected: current implementation fails because the n8n-safe wrapper does not exist yet.

- [ ] **Step 2: Implement the wrapper**

The wrapper should read JSON from stdin or `--event-file`, reject malformed payloads, enforce Openclaw team and `agent:ready`, suppress configured risk labels, and call the existing queue append logic rather than duplicating queue format rules. It should return secret-free JSON such as:

```json
{ "status": "accepted", "identifier": "OPN-235", "queued": true }
```

```json
{ "status": "duplicate", "identifier": "OPN-235", "queued": false }
```

```json
{ "status": "suppressed", "identifier": "OPN-235", "reason": "missing-agent-ready", "queued": false }
```

```json
{ "status": "rejected", "reason": "invalid-payload", "queued": false }
```

- [ ] **Step 3: Add duplicate suppression coverage**

Run the same event twice against a temporary queue file. Expected: first run reports accepted/queued; second run reports duplicate/suppressed and leaves one queue record.

- [ ] **Step 4: Add non-qualifying suppression coverage**

Test at least one missing `agent:ready` payload, one non-Openclaw-team payload, and one risk-label payload. Expected: each returns a secret-free suppressed result and writes no queue record.

- [ ] **Step 5: Add notification decision coverage**

Test that a qualifying smoke event produces the documented notification/pickup event or draft message path, without requiring a live Slack/notification send.

### Task 3: Verify And Update Linear

**Files:**
- Check: OpenClaw source checkout
- Check: Linear `OPN-225`
- Check: Linear `OPN-235`

- [ ] **Step 1: Run focused tests**

Run the OpenClaw test commands that cover the new handoff and replay fixtures.

- [ ] **Step 2: Run secret scan on changed files**

Run a focused secret scan or at minimum inspect `git diff` to confirm no tokens, private keys, `.env` values, session logs, runtime queue records, or notification payload bodies were committed.

- [ ] **Step 3: Document the n8n contract**

Update `OPN-225` with:

```markdown
OpenClaw internal handoff contract:
- Delivery mechanism:
- Command/path:
- Accepted payload fields:
- Accepted result shape:
- Suppressed result shape:
- Duplicate result shape:
- Verification commands:
- Rollback:
```

- [ ] **Step 4: Final `OPN-235` update**

Add a Linear comment with outcome, changed files, verification commands and results, commit hash/branch if present, rollback, and remaining follow-ups.
