# Linear OpenClaw n8n Handoff Design

## Purpose

Linear issue webhooks should enter through the media-host n8n container, not through a public OpenClaw runtime route. n8n verifies and filters the event, then calls OpenClaw over the existing internal SSH helper pattern used by the Jellyfin rating prompt workflow.

This design updates the shared understanding for:

- `OPN-225` parent investigation and verification record.
- `OPN-233` stale direct Linear webhook cleanup.
- `OPN-234` Docker/media-host n8n ingress.
- `OPN-235` OpenClaw-side internal handoff command.

## Decision

Use n8n as the public Linear webhook endpoint, with a repo-managed verifier script for real Linear signature verification in the first pass.

The recommended implementation is:

```text
Linear
  -> https://n8n.home.lab/webhook/linear-openclaw-pickup
  -> n8n workflow
  -> /opt/n8n-scripts/verify-linear-openclaw-pickup.js
  -> /opt/n8n-scripts/send-linear-openclaw-pickup.sh
  -> SSH to OpenClaw
  -> tools/bin/openclaw-linear-n8n-handoff --event-file <payload>
  -> tracking/linear-pickup-events/pending.jsonl
  -> OpenClaw notification or pickup decision path
```

## Why This Shape

The existing Docker repo already has the correct cross-host pattern for `jellyfin-rating-prompt`:

- n8n owns the webhook endpoint.
- n8n calls a repo-managed helper script mounted at `/opt/n8n-scripts`.
- The helper SSHes to `OPENCLAW_SSH_HOST` using the mounted OpenClaw tunnel key.
- The remote command runs inside `OPENCLAW_WORKSPACE`.

The Linear pickup path should follow that pattern instead of exposing OpenClaw directly or adding another public service.

## Media Host Responsibilities (`OPN-234`)

The media-host Docker repo owns:

- n8n workflow export: `apps/utilities/n8n/workflows/linear-openclaw-pickup.workflow.json`.
- Signature verifier script: `apps/utilities/n8n/scripts/verify-linear-openclaw-pickup.js`.
- OpenClaw delivery helper: `apps/utilities/n8n/scripts/send-linear-openclaw-pickup.sh`.
- Non-secret environment variable names in `apps/utilities/compose.yml` and `apps/utilities/example.env`.

The real Linear webhook signing secret must stay outside Git in Komodo or n8n runtime configuration.

The workflow must:

- Listen on `linear-openclaw-pickup`.
- Pass the raw request body and Linear headers to the verifier before parsing/filtering.
- Verify `Linear-Signature` using HMAC-SHA256 over the raw body with `LINEAR_OPENCLAW_WEBHOOK_SECRET`.
- Preserve `Linear-Delivery` and `Linear-Event` for evidence and idempotency.
- Accept only Linear issue create/update events for the Openclaw team.
- Require the deliberate pickup gate, initially `agent:ready`.
- Emit secret-free `accepted`, `suppressed`, or `rejected` evidence.
- Call OpenClaw only for `accepted` events.

If n8n cannot provide the exact raw body needed for HMAC verification, do not ship a fake verification step. Stop and either adjust the n8n webhook configuration to expose the raw body or replace this with a tiny Docker-side verifier endpoint as a separate explicit design change.

## OpenClaw Responsibilities (`OPN-235`)

OpenClaw owns the stable internal command contract that n8n calls over SSH.

Preferred command:

```bash
tools/bin/openclaw-linear-n8n-handoff --event-file <payload-json>
```

The command should:

- Accept only normalized JSON from n8n.
- Validate the payload shape again on the OpenClaw side.
- Enforce Openclaw team and `agent:ready` safety gates.
- Suppress configured risk labels with secret-free evidence.
- Append one queue record to `tracking/linear-pickup-events/pending.jsonl` or the existing durable queue.
- Reuse the existing `PickupCandidate` and duplicate suppression behavior if present.
- Return machine-readable JSON for `accepted`, `duplicate`, `suppressed`, or `rejected`.
- Trigger or document the notification/pickup decision path without bypassing approval gates.

The OpenClaw command must not require a public HTTP listener. It can be a local CLI invoked over SSH.

## Payload Contract

The n8n-to-OpenClaw normalized payload should be minimal:

```json
{
  "event_id": "linear-delivery-id-or-derived-id",
  "event_type": "Issue",
  "action": "create",
  "received_at": "2026-07-05T00:00:00Z",
  "issue": {
    "id": "linear-issue-uuid",
    "identifier": "OPN-235",
    "title": "Example title",
    "url": "https://linear.app/alex-lawson/issue/OPN-235/example",
    "team_key": "OPN",
    "team_name": "Openclaw",
    "state": "Todo",
    "labels": ["agent:ready"],
    "priority": "Medium"
  }
}
```

The verifier should reject or suppress events before this payload reaches OpenClaw when:

- Signature verification fails.
- The event is not a Linear issue event.
- The action is not create/update.
- The issue is not on the Openclaw team.
- The pickup gate is absent.
- Required fields are missing.

OpenClaw should still re-check the team and pickup gate because n8n is an integration boundary, not a trusted in-process caller.

## Ticket Boundaries

`OPN-233` remains about removing stale direct Linear-to-OpenClaw webhook configuration. It does not own the new n8n webhook.

`OPN-234` owns the Docker/media-host implementation and validation up to the SSH call.

`OPN-235` owns the OpenClaw command and queue/notification behavior behind that SSH call.

`OPN-225` should document the final end-to-end contract, verification commands, smoke evidence, and rollback path after `OPN-234` and `OPN-235` land.

## Verification

Media-host verification should include:

- Verifier unit tests or fixture runs for valid signature, invalid signature, malformed JSON, non-issue event, missing gate, and accepted issue event.
- `jq empty apps/utilities/n8n/workflows/linear-openclaw-pickup.workflow.json`.
- `sh -n apps/utilities/n8n/scripts/send-linear-openclaw-pickup.sh`.
- Docker Compose rendering with `apps/utilities/example.env`.

OpenClaw verification should include:

- Replay fixture for accepted create.
- Replay fixture for accepted update.
- Invalid payload shape.
- Duplicate suppression.
- Non-qualifying suppression.
- Notification/pickup decision output without requiring a live send.

End-to-end verification should include one gated Linear smoke issue after the n8n workflow and OpenClaw command are both deployed through the approved path.

## Rollback

Disable the n8n `linear-openclaw-pickup` workflow and remove or disable the Linear webhook pointing at it.

If the OpenClaw command is deployed separately, disable or revert that command and leave the queue untouched. Do not delete runtime queue records as part of rollback unless separately approved.
