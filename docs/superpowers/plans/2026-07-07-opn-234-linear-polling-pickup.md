# OPN-234 Linear Polling Pickup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the failed inbound Linear webhook approach with an OpenClaw-side poller that checks Linear every five minutes and queues eligible Openclaw issues exactly once.

**Architecture:** OpenClaw should own the poller because it owns the pickup queue, cursor, duplicate suppression, and local scheduler. The poller calls the Linear API outbound with a token stored outside Git, filters updated Openclaw issues through the existing `agent:ready` gates, and appends eligible candidates to `tracking/linear-pickup-events/pending.jsonl` only after the queue write succeeds.

**Tech Stack:** OpenClaw workspace Python/scripts, Linear GraphQL/API client, JSON cursor state, JSONL pickup queue, existing OpenClaw duplicate suppression and pickup gates, cron/systemd timer or an existing OpenClaw scheduler.

## Global Constraints

- Do not expose n8n, OpenClaw, or a webhook receiver publicly for this workflow.
- Store the real Linear API token outside Git and do not print it.
- Query only Openclaw issues updated since the last successful cursor.
- Require `agent:ready`.
- Suppress `agent:hold`, `manual`, and `no-agent`.
- Append to `tracking/linear-pickup-events/pending.jsonl` with duplicate suppression.
- Failed queue writes must not advance the cursor past unqueued eligible events.
- Rollback is disabling the scheduler or removing the polling job; leave existing queue files untouched.
- In this Docker repo, do not deploy, restart, pull, or recreate containers directly; Komodo remains the deployment source of truth.

---

## Current Repo Boundary

This checkout, `/home/oli/docker`, is the homelab Docker Compose repo. It contains the earlier n8n webhook implementation and the `apps/openclaw-gateway` container, but it does not contain the OpenClaw workspace files that own:

- `tracking/linear-pickup-events/pending.jsonl`
- existing pickup candidate parsing
- duplicate suppression by `event_id` or `identifier`
- the local OpenClaw scheduler
- the final autopickup or notification path

Do not implement the poller in this Docker repo unless the architecture is explicitly changed. Putting the queue writer in `apps/openclaw-gateway` would require new mounts, new secret scope, and a cross-container ownership change for OpenClaw runtime state.

## File Map

- Check: OpenClaw source workspace path, expected to be a separate checkout from `/home/oli/docker`.
  - Must contain or own the Linear pickup queue and existing pickup scripts.
- Modify or create in OpenClaw workspace: `tools/scripts/openclaw_linear_poll_pickup.py`
  - Poll Linear for updated Openclaw issues since the persisted cursor.
  - Normalize eligible issues to the existing pickup event shape.
  - Reuse existing queue append and duplicate suppression logic.
- Modify or create in OpenClaw workspace: `tools/bin/openclaw-linear-poll-pickup`
  - Stable CLI wrapper for manual runs and scheduler invocation.
- Modify or create in OpenClaw workspace: `tracking/linear-pickup-events/cursor.json`
  - Runtime cursor file; do not commit real runtime contents.
- Modify or create in OpenClaw workspace: scheduler config for the approved scheduler mechanism.
  - Prefer an existing OpenClaw scheduler if present.
  - Otherwise use a documented cron or systemd timer path for approval.
- Modify or create in OpenClaw workspace tests: focused tests for filtering, cursor advancement, queue failures, duplicate suppression, and repeat polls.
- Update in this Docker repo only if needed after approval: `docs/superpowers/specs/2026-07-06-opn-234-linear-polling-pickup-design.md`
  - Durable architecture note for the pivot away from inbound n8n.

### Task 1: Resolve Implementation Target

**Files:**
- Check: Linear `OPN-234`
- Check: `/home/oli/docker`
- Check: OpenClaw source workspace path

**Interfaces:**
- Consumes: Linear issue `OPN-234` acceptance criteria.
- Produces: confirmed OpenClaw source checkout path or a blocked Linear update.

- [x] **Step 1: Read OPN-234**

Fetched Linear `OPN-234` on 2026-07-07 and confirmed the current accepted architecture is OpenClaw-side outbound polling every five minutes, not public n8n webhook ingress.

- [x] **Step 2: Inspect this repo for the referenced local spec and queue owner**

Run:

```bash
rg -n "linear-pickup|openclaw-linear|OPN-234|poll|agent:ready|pending.jsonl|LINEAR" .
```

Observed: this repo contains the old n8n verifier/sender and the old n8n plan/spec, but not the referenced `docs/superpowers/specs/2026-07-06-opn-234-linear-polling-pickup-design.md` and not the OpenClaw queue implementation.

- [ ] **Step 3: Locate the OpenClaw source checkout**

Run only read-only commands first. Do not read `.env`, secrets, logs, session history, sqlite files, private keys, or runtime queue contents.

```bash
find /home /srv /opt -maxdepth 4 -type d \( -name .git -o -name tools \) 2>/dev/null
```

Expected: a source checkout that contains OpenClaw scripts and is safe to edit.

- [ ] **Step 4: Confirm target repo status**

Run from the OpenClaw source checkout:

```bash
git status --short --branch
rg --files | rg '(^tools/|^tests/|linear|pickup|tracking)'
```

Expected: source files are visible and no unrelated work needs to be overwritten.

- [ ] **Step 5: Block if the OpenClaw source checkout is unavailable**

If no editable source checkout is available, leave implementation untouched and comment on Linear:

```markdown
Pickup note for OPN-234:

I wrote the implementation plan in `/home/oli/docker/docs/superpowers/plans/2026-07-07-opn-234-linear-polling-pickup.md`.

Current blocker:
- The approved polling architecture belongs in the OpenClaw workspace because it owns `tracking/linear-pickup-events/pending.jsonl`, cursor state, duplicate suppression, and scheduling.
- The current `/home/oli/docker` checkout only contains Docker Compose, the old n8n webhook path, and `apps/openclaw-gateway`; implementing the poller here would change state ownership and secret scope.

Needed to proceed:
- Provide the editable OpenClaw source checkout path or mount it in this workspace.
- Confirm where the scheduler should live: existing OpenClaw scheduler, cron, or systemd timer.
```

### Task 2: Add Poller Tests In The OpenClaw Workspace

**Files:**
- Modify or create: OpenClaw tests for Linear polling pickup.
- Check: existing OpenClaw queue append tests, if present.

**Interfaces:**
- Consumes: existing queue append and duplicate suppression API.
- Produces: failing tests for poll filtering, cursor behavior, and duplicate suppression.

- [ ] **Step 1: Write a fixture for an eligible Linear issue**

Use this payload shape for tests, adapted to the existing OpenClaw test helpers:

```json
{
  "id": "linear-opn-234-smoke-id",
  "identifier": "OPN-234",
  "title": "Poller smoke pickup",
  "url": "https://linear.app/alex-lawson/issue/OPN-234/poller-smoke-pickup",
  "updatedAt": "2026-07-07T00:00:00.000Z",
  "team": { "key": "OPN", "name": "Openclaw" },
  "state": { "name": "In Progress", "type": "started" },
  "labels": { "nodes": [{ "name": "agent:ready" }, { "name": "tag:linear" }] }
}
```

Expected: test fails before implementation because the poller entry point does not exist.

- [ ] **Step 2: Write suppression tests**

Cover these cases:

```text
missing agent:ready -> suppressed, no queue write
agent:hold present -> suppressed, no queue write
manual present -> suppressed, no queue write
no-agent present -> suppressed, no queue write
team.name != Openclaw -> suppressed, no queue write
```

Expected: tests fail before implementation.

- [ ] **Step 3: Write cursor safety tests**

Use a fake Linear client returning two updated issues. Make the queue writer fail on the second eligible issue.

Expected behavior:

```text
first eligible issue is queued
second eligible issue returns a write failure
cursor is not advanced beyond the failed issue updatedAt
rerun can see the failed issue again
```

- [ ] **Step 4: Write duplicate suppression tests**

Run the same eligible issue twice against a temporary queue.

Expected behavior:

```text
first run appends one queue record
second run reports duplicate or already queued
queue still contains one record for the identifier/event id
```

### Task 3: Implement Manual Poller

**Files:**
- Modify or create: `tools/scripts/openclaw_linear_poll_pickup.py`
- Modify or create: `tools/bin/openclaw-linear-poll-pickup`

**Interfaces:**
- Consumes: `LINEAR_API_TOKEN` from the environment.
- Consumes: cursor file path option or default `tracking/linear-pickup-events/cursor.json`.
- Consumes: queue path option or default `tracking/linear-pickup-events/pending.jsonl`.
- Produces: secret-free JSON summary with counts for accepted, duplicate, suppressed, rejected, and failed.

- [ ] **Step 1: Add CLI wrapper**

The wrapper should execute the Python poller from the OpenClaw workspace and pass arguments through:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
exec python3 tools/scripts/openclaw_linear_poll_pickup.py "$@"
```

- [ ] **Step 2: Add poller arguments**

Support:

```text
--cursor-path tracking/linear-pickup-events/cursor.json
--queue-path tracking/linear-pickup-events/pending.jsonl
--since ISO-8601 timestamp for manual override
--dry-run to print decisions without writing queue/cursor
--limit Linear page size
```

- [ ] **Step 3: Query Linear issues updated since cursor**

Use the Linear API token from `LINEAR_API_TOKEN`. Do not print request headers or token values.

Filter in the query or post-query to:

```text
team key/name: Openclaw
updatedAt > cursor
include labels, state, title, identifier, url, priority
```

- [ ] **Step 4: Normalize eligible issues**

Produce the same queue candidate shape used by the existing OpenClaw handoff:

```json
{
  "event_id": "linear-poll:OPN-234:2026-07-07T00:00:00.000Z",
  "identifier": "OPN-234",
  "title": "Poller smoke pickup",
  "team": "Openclaw",
  "received_at": "2026-07-07T00:00:05Z",
  "action": "poll",
  "status": "In Progress",
  "status_type": "started",
  "labels": ["agent:ready", "tag:linear"],
  "url": "https://linear.app/alex-lawson/issue/OPN-234/poller-smoke-pickup"
}
```

- [ ] **Step 5: Reuse existing queue append and duplicate suppression**

Call the existing OpenClaw queue append helper. If no helper exists, extract one first from the current queue writer so n8n handoff and polling share duplicate semantics.

- [ ] **Step 6: Advance cursor only after writes are safe**

Advance the cursor to the maximum successfully processed `updatedAt` only after all eligible queue writes up to that point have succeeded. Suppressed issues can advance the cursor; failed eligible queue writes cannot.

### Task 4: Add Five-Minute Scheduler Path

**Files:**
- Modify or create: approved OpenClaw scheduler config.
- Update: deployment/runbook documentation if the scheduler is external to source.

**Interfaces:**
- Consumes: `tools/bin/openclaw-linear-poll-pickup`.
- Produces: a five-minute scheduled invocation or a scheduler change ready for explicit approval.

- [ ] **Step 1: Prefer existing OpenClaw scheduler**

If OpenClaw already has a scheduler, register:

```bash
tools/bin/openclaw-linear-poll-pickup
```

with a five-minute cadence and secret-free logs.

- [ ] **Step 2: Otherwise prepare a cron or systemd timer**

Use the host's existing service management convention. Do not install or enable it without approval if that mutates live state.

Expected cadence:

```text
every 5 minutes
```

- [ ] **Step 3: Document scheduler rollback**

Rollback:

```text
disable the timer/cron entry/scheduler job
leave tracking/linear-pickup-events/pending.jsonl and cursor state untouched
```

### Task 5: Verify With Linear Smoke

**Files:**
- Check: OpenClaw source checkout.
- Check: Linear `OPN-234`, `OPN-225`, and `OPN-235`.

**Interfaces:**
- Consumes: a real Linear API token stored outside Git.
- Produces: ticket evidence and final status.

- [ ] **Step 1: Run focused tests**

Run the OpenClaw test command covering the poller and queue behavior.

- [ ] **Step 2: Run manual dry-run**

Run:

```bash
LINEAR_API_TOKEN=<from-secure-runtime-env> tools/bin/openclaw-linear-poll-pickup --dry-run
```

Expected: output is secret-free and lists accepted/suppressed counts.

- [ ] **Step 3: Run live gated smoke**

Create or update a real Openclaw Linear issue with `agent:ready`, then run:

```bash
tools/bin/openclaw-linear-poll-pickup
```

Expected: exactly one queue record is appended for the smoke issue.

- [ ] **Step 4: Run repeat poll**

Run:

```bash
tools/bin/openclaw-linear-poll-pickup
```

Expected: duplicate suppression prevents a second queue record.

- [ ] **Step 5: Update Linear**

Comment on `OPN-234`, `OPN-225`, and `OPN-235` with:

```markdown
Outcome:
Changed files:
Scheduler path:
Verification:
Live smoke issue:
Duplicate suppression evidence:
Rollback:
Commit:
Remaining follow-ups:
```
