> **Archived/stale plan:** This OPN-271 slice plan is preserved for historical context only. Do not implement from this file directly. Use `docs/superpowers/plans/2026-07-12-opn-271-plane-webhook-desired-state.md` as the current implementation plan for OPN-271.

# OPN-271 Plane Queue Smoke Shape Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the optional gateway smoke check verify that the Plane webhook queue diagnostics response includes the expected non-secret count fields.

**Architecture:** Keep `CHECK_PLANE_WEBHOOK_QUEUE=1` opt-in. The smoke script should save the authenticated queue response to a temporary file, verify HTTP 200, then check for required diagnostic field names without printing the gateway token or raw response body. Tests use the existing fake `curl` harness.

**Tech Stack:** Bash smoke script, pytest subprocess tests, fake curl fixture, README documentation.

## Global Constraints

- Do not call the dispatch endpoint.
- Do not mutate live queues, containers, Plane, n8n, or Docker state.
- Do not print gateway tokens or queue response bodies.
- Keep the Plane queue smoke check opt-in through `CHECK_PLANE_WEBHOOK_QUEUE=1`.

---

### Task 1: Smoke Script Tests

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_smoke_script.py`

**Interfaces:**
- Consumes: `scripts/smoke-openclaw-gateway.sh`
- Produces: tests for queue diagnostic JSON shape validation.

- [x] **Step 1: Extend fake curl to write Plane queue bodies**

Update `write_fake_curl()` so the fake curl records any `-o <path>` argument and writes a configurable Plane queue JSON response body for `/v1/workflow/plane/webhook/queue`.

- [x] **Step 2: Add a failing missing-field test**

Add `test_smoke_script_reports_plane_webhook_queue_missing_field` that returns HTTP 200 with a Plane queue body missing `pending_count`. Assert return code `1`, stderr includes `Plane webhook queue response missing pending_count.`, and `gateway-secret` is not printed.

- [x] **Step 3: Run focused smoke tests and verify red**

Run:

```bash
python -m pytest apps/openclaw-gateway/openclaw-gateway/tests/test_smoke_script.py::test_smoke_script_can_check_plane_webhook_queue_status apps/openclaw-gateway/openclaw-gateway/tests/test_smoke_script.py::test_smoke_script_reports_plane_webhook_queue_missing_field -q
```

Expected: the new missing-field test fails before implementation because the smoke script only checks HTTP status.

### Task 2: Smoke Script Validation

**Files:**
- Modify: `scripts/smoke-openclaw-gateway.sh`

**Interfaces:**
- Produces: field validation for `queued_count`, `dedupe_count`, `dispatched_count`, `pending_count`, and `malformed_count`.

- [x] **Step 1: Capture queue response to a temp file**

Use `mktemp`, register cleanup with `trap`, and update the Plane queue curl to write the response body to the temp file while still capturing `%{http_code}`.

- [x] **Step 2: Validate required fields locally**

After confirming HTTP 200, loop over required field names and use a quiet text check against the temp file. On a missing field, print `Plane webhook queue response missing <field>.` to stderr and exit `1`.

- [x] **Step 3: Verify focused smoke tests pass**

Run:

```bash
python -m pytest apps/openclaw-gateway/openclaw-gateway/tests/test_smoke_script.py::test_smoke_script_can_check_plane_webhook_queue_status apps/openclaw-gateway/openclaw-gateway/tests/test_smoke_script.py::test_smoke_script_reports_plane_webhook_queue_missing_field -q
```

Expected: pass.

### Task 3: Docs, Verification, Commit, Linear

**Files:**
- Modify: `apps/openclaw-gateway/README.md`
- Modify: `docs/superpowers/plans/2026-07-11-opn-271-plane-queue-smoke-shape.md`

**Interfaces:**
- Produces: documented opt-in smoke behavior and final Linear checkpoint.

- [x] **Step 1: Document queue smoke shape check**

Update the smoke-test README section to say the optional Plane queue smoke check verifies HTTP 200 and required diagnostic count fields without printing the token or body.

- [x] **Step 2: Run verification**

Run:

```bash
python -m pytest apps/openclaw-gateway/openclaw-gateway/tests/test_smoke_script.py -q
docker compose -f apps/openclaw-gateway/compose.yml --env-file apps/openclaw-gateway/example.env config --quiet
git diff --check
```

Run a focused changed-file secret scan.

- [ ] **Step 3: Commit and update Linear**

Commit with:

```bash
git commit -m "OPN-271: validate Plane queue smoke shape"
```

Update OPN-271 and OPN-264 with commit hash, verification, and remaining live gaps.
