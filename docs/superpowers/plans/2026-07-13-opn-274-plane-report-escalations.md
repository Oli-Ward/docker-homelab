# OPN-274 Plane Report Escalation Slice

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:executing-plans or the local implementation workflow to execute
> this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing read-only n8n Plane workflow report so it
produces actionable escalation data for `Blocked`, `Needs Input`, and stale
`In Review` work without writing to Plane, Slack, GitHub, Docker, or Komodo.

**Architecture:** Keep the existing disabled n8n workflow and Node report
script. Safely expose Plane work item timestamps through the Plane SDK/gateway
model, then have the report script classify actionable items from the compact
gateway response. The output remains JSON only and is suitable input for a
future Slack digest workflow.

**Boundaries:**

- No live Docker, Komodo, n8n activation, Plane writes, Slack posts, or GitHub
  writes.
- No real credentials in repo files, tests, docs, workflow exports, or output.
- Preserve raw Plane payload exclusion at the gateway response boundary.
- Keep workflow exports disabled with `active: false`.

## Task 1: Expose Safe Timestamp Fields

**Files:**

- Modify: `packages/openclaw-plane-sdk/src/openclaw_plane_sdk/models.py`
- Modify: `packages/openclaw-plane-sdk/src/openclaw_plane_sdk/client.py`
- Modify: `packages/openclaw-plane-sdk/tests/test_plane_client.py`

- [x] Add optional `created_at` and `updated_at` fields to `PlaneWorkItem`.
- [x] Map `created_at` and `updated_at` from Plane responses in `_work_item`.
- [x] Add a client test proving timestamps survive normalization while raw
  payload remains separate.

## Task 2: Add Escalation Report Classification

**Files:**

- Modify: `apps/utilities/n8n/scripts/plane-workflow-report.js`
- Modify: `apps/utilities/n8n/scripts/test-plane-workflow-report.js`

- [x] Include `created_at` and `updated_at` in compact item summaries when
  present.
- [x] Add `needs_input_count`, `in_review_count`, `stale_in_review_count`,
  `actionable_count`, and `actionable_items` to the report.
- [x] Classify `Blocked`, `Needs Input`, and stale `In Review` items as
  actionable.
- [x] Make stale thresholds configurable through function options and env vars:
  `PLANE_REPORT_NEEDS_INPUT_HOURS`, `PLANE_REPORT_BLOCKED_HOURS`, and
  `PLANE_REPORT_IN_REVIEW_HOURS`.
- [x] Keep malformed/missing timestamps conservative: never mark an item stale
  only because the timestamp is absent or invalid.
- [x] Assert raw payloads, descriptions, and credentials are not forwarded.

## Task 3: Workflow Contract And Docs

**Files:**

- Modify: `apps/utilities/compose.yml`
- Modify: `apps/utilities/example.env`
- Modify: `docs/workflow/plane.md`
- Modify: `docs/superpowers/specs/2026-07-12-opn-274-n8n-plane-automation-spec.md`

- [x] Pass the new threshold env vars through to n8n with safe defaults.
- [x] Document the escalation fields, thresholds, rollback switch, and the
  future Slack digest handoff.
- [x] Keep the existing workflow import path and disabled export unchanged.
- [x] Add an `Execute Workflow Trigger` to the disabled workflow export so live
  n8n can run a manual smoke without waiting for the weekly schedule.

## Task 4: Verification

- [x] `node apps/utilities/n8n/scripts/test-plane-workflow-report.js`
- [x] `node apps/utilities/n8n/scripts/test-plane-workflow-report-workflow.js`
- [x] `PYTHONPATH=src pytest tests/test_plane_client.py`
- [x] `docker compose -f apps/utilities/compose.yml --env-file apps/utilities/example.env config --quiet`
- [x] `git diff --check`

## Task 5: Live Deployment And Smoke

- [x] Deploy the `utilities` stack through Komodo.
- [x] Confirm the live `n8n` container has the Plane report env vars and new
  threshold env vars present.
- [x] Import the updated `plane-workflow-report` workflow into live n8n with
  the manual smoke trigger.
- [x] Reactivate and restart `n8n` through Komodo so the active workflow
  registry reloads the updated definition.
- [x] Run the live workflow through n8n CLI with an alternate broker port.
- [x] Capture non-secret smoke evidence:
  - execution status: `success`
  - last node: `Parse Plane Workflow Report`
  - total Plane items read: `100`
  - actionable items: `0`

## Completion Note

Linear OPN-274 and the Plane mirror were updated to `Done` after the live n8n
workflow was imported, reactivated, restarted through Komodo, and smoked
successfully against Plane. No follow-up live smoke work remains for this slice.
