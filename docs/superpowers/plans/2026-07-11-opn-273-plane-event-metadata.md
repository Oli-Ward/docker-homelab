# OPN-273 Plane Event Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Propagate safe normalized Plane work-item metadata through webhook queueing, n8n dispatch, and the OpenClaw sender so downstream agent pickup can evaluate `Ready for Agent` events without raw Plane payload access.

**Architecture:** Extract a small allowlisted set of work-item metadata from Plane webhook `data` into the existing normalized event. Forward the same safe fields through the gateway n8n client and n8n SSH sender. Do not forward raw payloads, descriptions, comments, webhook signatures, tokens, or arbitrary nested objects.

**Tech Stack:** FastAPI webhook route, file-backed gateway queue, n8n HTTP client, shell/Node sender script, pytest route/client tests, Node script tests.

---

### Task 1: Gateway Normalization Tests

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py`

- [x] **Step 1: Write failing webhook normalization test**

Extend `test_plane_webhook_accepts_signed_issue_event_without_gateway_bearer_token` so the signed Plane `data` contains:

- `id`
- `project_id`
- `sequence_id`
- `name`
- `state_id`
- `state` object with `name`
- `priority`
- `labels`
- `description_html` sentinel that must not be forwarded

Assert the acknowledgement and queued JSONL record include only safe normalized fields:

- `project_id`
- `sequence_id`
- `name`
- `state_id`
- `state_name`
- `priority`
- `label_names`

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_workflow_routes.py::test_plane_webhook_accepts_signed_issue_event_without_gateway_bearer_token -q
```

Expected: fail because the webhook route currently drops those metadata fields.

### Task 2: n8n Forwarding Tests

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_n8n_client.py`
- Modify: `apps/utilities/n8n/scripts/test-send-plane-openclaw-dispatch.js`

- [x] **Step 1: Write failing n8n client test expectations**

Extend `test_n8n_forward_plane_webhook_event_posts_normalized_payload` to include the same safe metadata fields and assert they appear in the HTTP JSON body.

- [x] **Step 2: Write failing sender test expectations**

Extend `test-send-plane-openclaw-dispatch.js` to include the same safe metadata fields in input and expected uploaded payload, while still proving `raw_payload` is not forwarded.

### Task 3: Implementation

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/workflow.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/n8n.py`
- Modify: `apps/utilities/n8n/scripts/send-plane-openclaw-dispatch.sh`
- Modify: `apps/openclaw-gateway/README.md`
- Modify: `docs/workflow/plane.md`

- [x] **Step 1: Add optional safe metadata fields**

Add optional fields to `PlaneWebhookAck` for `project_id`, `sequence_id`, `name`, `state_id`, `state_name`, `priority`, and `label_names`.

- [x] **Step 2: Extract safe metadata from webhook data**

Add local helper functions in `workflow.py` that extract only scalar/string-list metadata from `payload["data"]`. Reject nested arbitrary objects except recognized `state.name` and label `name` values.

- [x] **Step 3: Forward safe metadata through n8n**

Update `N8nClient.forward_plane_webhook_event()` and `send-plane-openclaw-dispatch.sh` to preserve the allowlisted metadata fields.

- [x] **Step 4: Document the normalized event contract**

Update gateway and Plane workflow docs to show the enriched normalized event and reiterate that raw Plane payloads/descriptions/comments are not forwarded.

### Task 4: Verification, Commit, Linear

**Files:**
- Modify: `docs/superpowers/plans/2026-07-11-opn-273-plane-event-metadata.md`

- [x] **Step 1: Verify**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_workflow_routes.py tests/test_n8n_client.py -q
node apps/utilities/n8n/scripts/test-send-plane-openclaw-dispatch.js
docker compose -f apps/openclaw-gateway/compose.yml --env-file apps/openclaw-gateway/example.env config --quiet
docker compose -f apps/utilities/compose.yml --env-file apps/utilities/example.env config --quiet
git diff --check
```

Expected: all commands exit 0.

- [x] **Step 2: Commit and update Linear**

Commit with:

```bash
git commit -m "OPN-273: propagate safe Plane event metadata"
```

Update OPN-273 and OPN-264 with commit hash, verification, and remaining live pickup gaps.
