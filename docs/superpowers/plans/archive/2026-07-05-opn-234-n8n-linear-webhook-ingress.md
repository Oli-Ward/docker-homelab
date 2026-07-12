# OPN-234 n8n Linear Webhook Ingress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install an n8n Linear webhook ingress that validates Linear events and forwards only gated Openclaw pickup events through the approved OpenClaw internal handoff.

**Architecture:** The public Linear webhook terminates at n8n on `https://n8n.home.lab/webhook/linear-openclaw-pickup`. n8n passes the raw request body and Linear headers to a repo-managed verifier script, verifies the Linear signature before filtering issue create/update events to the Openclaw team and the `agent:ready` gate, then calls a repo-managed SSH helper script that delivers a normalized payload to OpenClaw. OPN-235 owns the OpenClaw command behind that SSH call.

**Tech Stack:** Docker Compose, n8n workflow JSON, POSIX shell helper scripts, Linear webhooks, OpenClaw internal handoff from OPN-235.

---

## Cross-Host Design

The approved design is captured in `docs/superpowers/specs/2026-07-05-linear-openclaw-n8n-handoff-design.md`.

OPN-234 owns the media-host Docker/n8n half:

```text
Linear
  -> https://n8n.home.lab/webhook/linear-openclaw-pickup
  -> n8n workflow
  -> /opt/n8n-scripts/verify-linear-openclaw-pickup.js
  -> /opt/n8n-scripts/send-linear-openclaw-pickup.sh
  -> SSH to OpenClaw
```

OPN-235 owns the OpenClaw command that runs after SSH, preferably:

```text
tools/bin/openclaw-linear-n8n-handoff --event-file <payload-json>
```

The Docker-side workflow can be implemented against this command contract, but live end-to-end completion still requires the OpenClaw command to exist and pass its own queue/notification tests.

## File Map

- Modify: `apps/utilities/compose.yml`
  - Add non-secret n8n environment variable names needed by the workflow and helper script.
- Modify: `apps/utilities/example.env`
  - Document safe placeholders for the Linear webhook secret variable name and the OpenClaw handoff settings defined by OPN-235.
- Create: `apps/utilities/n8n/workflows/linear-openclaw-pickup.workflow.json`
  - n8n workflow export for the Linear webhook path, signature check, filters, normalized payload, logging, and OpenClaw handoff call.
- Create: `apps/utilities/n8n/scripts/verify-linear-openclaw-pickup.js`
  - Node verifier for `Linear-Signature` using HMAC-SHA256 over the raw request body and `LINEAR_OPENCLAW_WEBHOOK_SECRET`.
- Create: `apps/utilities/n8n/scripts/send-linear-openclaw-pickup.sh`
  - Helper script that reads normalized JSON from stdin and calls the OPN-235-approved OpenClaw internal interface without printing secrets.
- Modify: `README.md`
  - Add any user-facing architecture note only if the workflow becomes an active service path after OPN-235 is complete.
- Check: `docs/superpowers/plans/2026-07-05-opn-234-n8n-linear-webhook-ingress.md`
  - Keep this plan updated with the exact OPN-235 contract before implementation.

## OPN-235 Contract Status

Current OPN-235 progress from Linear comments:

- Existing queue receiver: `tools/scripts/openclaw_linear_pickup_webhook.py`
- Existing queue path: `tracking/linear-pickup-events/pending.jsonl`
- Existing queue record shape: `PickupCandidate`
- Existing duplicate suppression: append logic suppresses duplicates by `event_id` or issue `identifier`
- Existing autopickup surfaces: `tools/scripts/openclaw_linear_autopickup.py` and `tools/bin/openclaw-linear-autopickup`
- Existing notification wrapper: `tools/bin/openclaw-notify`
- Existing gate: receiver requires `agent:ready` by default
- Current constraint: autopickup is dry-run/fixture-first; `--apply` is intentionally unwired and exits with an error
- Current constraint: notification wrapper is draft by default; explicit sends require `--send` and live send remains approval-gated
- Recommended OPN-235 implementation path: add an internal n8n-safe handoff wrapper/command in the OpenClaw workspace that accepts normalized JSON from n8n, validates the already-filtered payload shape, appends the existing queue record exactly once, and covers duplicate/non-qualifying/qualifying notification behavior with tests or replay fixtures.

Required contract for the Docker-side helper:

- Delivery mechanism: SSH to `OPENCLAW_SSH_HOST`, `cd "$OPENCLAW_WORKSPACE"`, then run `tools/bin/openclaw-linear-n8n-handoff --event-file <payload-json>`.
- Required payload fields: `event_id`, `event_type`, `action`, `received_at`, and an `issue` object containing `id`, `identifier`, `title`, `url`, `team_key`, `team_name`, `state`, `labels`, and `priority`.
- Success response: machine-readable JSON with `status: "accepted"` or equivalent.
- Suppression response: machine-readable JSON with `status: "suppressed"` and a secret-free reason.
- Duplicate behavior: machine-readable JSON with `status: "duplicate"` and no second queue append.
- Verification command: OpenClaw replay tests for accepted create/update, invalid payload, duplicate suppression, non-qualifying suppression, and notification decision output.
- Rollback: disable the n8n workflow and/or revert/disable the OpenClaw command without deleting runtime queue records.

### Task 1: Record Blocked Status

**Files:**
- Create: `docs/superpowers/plans/2026-07-05-opn-234-n8n-linear-webhook-ingress.md`
- Check: Linear `OPN-234`
- Check: Linear `OPN-235`

- [x] **Step 1: Read OPN-234**

Run: fetch Linear issue `OPN-234`.
Expected: issue requests n8n as the public Linear webhook ingress and requires accepted events to call the approved OpenClaw handoff from the companion ticket.

- [x] **Step 2: Read OPN-235**

Run: fetch Linear issue `OPN-235`.
Expected: issue is the companion OpenClaw-side handoff work.

- [x] **Step 3: Record initial blocker assessment**

Initial observation on 2026-07-05: OPN-235 was `Backlog`, so the first pass treated OPN-234 as blocked until the OpenClaw command contract existed. This was later refined: OPN-234 can implement the Docker/n8n workflow and helper against the agreed command contract while OPN-235 implements the OpenClaw command.

- [x] **Step 4: Update Linear**

Set `OPN-234` to `Blocked` and add a comment:

```markdown
Picked this up and wrote the initial plan at `docs/superpowers/plans/2026-07-05-opn-234-n8n-linear-webhook-ingress.md`.

Initial blocker note: OPN-234 requires n8n to forward accepted events to the approved OpenClaw internal handoff from OPN-235, and at that point the handoff contract was not defined yet.

No repo runtime config or live Docker state was changed.

Next action: complete or define the OPN-235 interface contract, then resume OPN-234 using the saved plan.
```

- [x] **Step 5: Refresh after OPN-235 progress**

Observed on 2026-07-05: OPN-235 moved to `In Progress` and identified existing OpenClaw surfaces, including `tools/scripts/openclaw_linear_pickup_webhook.py`, `tracking/linear-pickup-events/pending.jsonl`, `PickupCandidate`, `tools/bin/openclaw-linear-autopickup`, and `tools/bin/openclaw-notify`. The final n8n-safe handoff wrapper/command is still not defined or landed, so OPN-234 remains blocked.

### Task 2: Resume After OPN-235 Defines The Interface

**Files:**
- Modify: `docs/superpowers/plans/2026-07-05-opn-234-n8n-linear-webhook-ingress.md`
- Check: Linear `OPN-235`

- [ ] **Step 1: Read OPN-235 final comment or description**

Run: fetch Linear issue `OPN-235` and its comments.
Expected: an exact internal handoff contract exists and includes delivery mechanism, payload shape, duplicate handling, verification, and rollback.

- [x] **Step 2: Refresh the contract section in this plan with current OPN-235 progress**

Updated `OPN-235 Contract Status` with the concrete existing surfaces from OPN-235 comments. Keep secrets out of the plan.

- [ ] **Step 3: Replace the remaining contract gaps after OPN-235 lands the wrapper**

Update `OPN-235 Contract Status` with the exact n8n-callable wrapper/command, required payload fields, return semantics, verification command, and rollback. Keep secrets out of the plan.

- [ ] **Step 4: Move OPN-234 to In Progress**

Use Linear state `In Progress` only after the OPN-235 handoff contract exists.

### Task 3: Implement The n8n Workflow

**Files:**
- Modify: `apps/utilities/compose.yml`
- Modify: `apps/utilities/example.env`
- Create: `apps/utilities/n8n/workflows/linear-openclaw-pickup.workflow.json`
- Create: `apps/utilities/n8n/scripts/verify-linear-openclaw-pickup.js`
- Create: `apps/utilities/n8n/scripts/send-linear-openclaw-pickup.sh`

- [x] **Step 1: Add environment placeholders**

Add only non-secret variable names and safe defaults to `apps/utilities/example.env`. The real `LINEAR_OPENCLAW_WEBHOOK_SECRET` must stay in Komodo or the live n8n credential store, not Git.

- [x] **Step 2: Add n8n workflow JSON**

Create the workflow export with:

- Webhook path: `linear-openclaw-pickup`
- Method: `POST`
- Execute Command node calling `/opt/n8n-scripts/verify-linear-openclaw-pickup.js` before filtering or forwarding
- Event filter: Linear issue create/update events only
- Team filter: Openclaw team only
- Gate filter: `agent:ready` label or equivalent OPN-235-approved gate only
- Normalized payload: minimum fields accepted by OPN-235
- Durable, secret-free accepted/rejected/suppressed logging
- Execute Command node calling `/opt/n8n-scripts/send-linear-openclaw-pickup.sh`

- [x] **Step 3: Add verifier script**

Create `apps/utilities/n8n/scripts/verify-linear-openclaw-pickup.js`. It must compute HMAC-SHA256 over the exact raw request body and compare it to the `Linear-Signature` header before parsing JSON. It should return one secret-free JSON result:

```json
{ "status": "accepted", "payload": {} }
```

```json
{ "status": "suppressed", "reason": "missing-agent-ready" }
```

```json
{ "status": "rejected", "reason": "invalid-signature" }
```

- [x] **Step 4: Add helper script**

Create `apps/utilities/n8n/scripts/send-linear-openclaw-pickup.sh` as a POSIX shell script that reads one JSON event from stdin and calls the exact OPN-235-approved handoff. The script must not echo secrets, payload bodies, SSH keys, bearer tokens, or Linear signature material.

### Task 4: Validate Without Deployment

**Files:**
- Check: `apps/utilities/compose.yml`
- Check: `apps/utilities/example.env`
- Check: `apps/utilities/n8n/workflows/linear-openclaw-pickup.workflow.json`
- Check: `apps/utilities/n8n/scripts/verify-linear-openclaw-pickup.js`
- Check: `apps/utilities/n8n/scripts/send-linear-openclaw-pickup.sh`

- [x] **Step 1: Validate workflow JSON**

Run:

```bash
jq empty apps/utilities/n8n/workflows/linear-openclaw-pickup.workflow.json
```

Expected: exits 0 with no output.

- [x] **Step 2: Validate verifier behavior**

Run verifier fixture tests or direct node invocations for valid signature, invalid signature, malformed JSON, non-issue event, missing gate, and accepted issue event.

- [x] **Step 3: Validate shell syntax**

Run:

```bash
sh -n apps/utilities/n8n/scripts/send-linear-openclaw-pickup.sh
```

Expected: exits 0 with no output.

- [x] **Step 4: Validate Compose rendering**

Run:

```bash
docker compose --env-file apps/utilities/example.env -f apps/utilities/compose.yml config
```

Expected: exits 0 and renders the utilities stack without deploying or recreating containers.

- [x] **Step 5: Check diff hygiene**

Run:

```bash
git diff --check
```

Expected: exits 0 with no whitespace errors.

### Task 5: Live Follow-Up After Repo Changes

**Files:**
- Check: Linear `OPN-234`
- Check: Linear `OPN-225`

- [ ] **Step 1: Deploy through Komodo**

Use Komodo to redeploy the utilities stack. Do not run `docker compose up`, `docker compose down`, `docker compose pull`, or restart containers directly from this repo.

- [ ] **Step 2: Configure Linear webhook**

Create or update the Linear webhook to call:

```text
https://n8n.home.lab/webhook/linear-openclaw-pickup
```

Store the webhook signing secret outside Git.

- [ ] **Step 3: Run smoke issue**

Create or update a Linear smoke issue for the Openclaw team with the required pickup gate. Confirm n8n receives the event and OpenClaw records exactly one accepted handoff.

- [ ] **Step 4: Update Linear closeout**

Add final comments to `OPN-234` and `OPN-225` with the workflow name, URL shape without secrets, verification evidence, rollback path, commit hash, and remaining follow-ups.
