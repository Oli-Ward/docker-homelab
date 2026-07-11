# OPN-273 Plane Pickup Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only Plane agent-pickup preview helper that classifies normalized Plane events as ignored, ready, or needs-input without starting Codex or writing to Plane.

**Architecture:** Build a Node.js script in the repo-managed n8n scripts directory. It reads one normalized Plane dispatch event from stdin or a file, evaluates the documented `Ready for Agent` metadata contract, and prints a compact JSON decision. It performs no network, SSH, Docker, Plane, GitHub, or OpenClaw actions.

**Tech Stack:** Node.js built-ins, n8n scripts directory, focused Node tests, docs.

---

### Task 1: Preview Script Tests

**Files:**
- Add: `apps/utilities/n8n/scripts/test-plane-agent-pickup-preview.js`

- [x] **Step 1: Write failing classification tests**

Create tests that execute `plane-agent-pickup-preview.js` with fixture events and assert:

- `ignored` for non-issue events
- `ignored` for tickets not in `Ready for Agent`
- `needs_input` for `Ready for Agent` without a repo label
- `ready` for `Ready for Agent` with `repo:<name>`
- output includes `correlation_id`, `resource_id`, `project_id`, `sequence_id`, `state_name`, `repo`, and `reason`
- descriptions/raw payload sentinels are not copied to output

Run:

```bash
node apps/utilities/n8n/scripts/test-plane-agent-pickup-preview.js
```

Expected: fail because `plane-agent-pickup-preview.js` does not exist.

### Task 2: Preview Script Implementation

**Files:**
- Add: `apps/utilities/n8n/scripts/plane-agent-pickup-preview.js`

- [x] **Step 1: Implement pure classifier**

Export `classifyPlaneAgentPickup(event)` and implement CLI mode. The script should accept an optional event file path as `argv[2]`; otherwise read stdin.

- [x] **Step 2: Keep output compact and safe**

Output only:

- `source: "plane"`
- `preview: "agent-pickup"`
- `decision`
- `reason`
- `correlation_id`
- `resource_id`
- `project_id`
- `sequence_id`
- `state_name`
- `priority`
- `labels`
- `repo`
- `ticket_name`

### Task 3: Docs, Verification, Commit, Linear

**Files:**
- Modify: `docs/workflow/plane.md`
- Modify: `apps/openclaw-gateway/README.md`
- Modify: `docs/superpowers/plans/2026-07-11-opn-273-plane-pickup-preview.md`

- [x] **Step 1: Document dry-run preview helper**

Document the helper as repo-managed, read-only, and not live-enabled by default.

- [x] **Step 2: Verify**

Run:

```bash
node apps/utilities/n8n/scripts/test-plane-agent-pickup-preview.js
node apps/utilities/n8n/scripts/test-send-plane-openclaw-dispatch.js
docker compose -f apps/utilities/compose.yml --env-file apps/utilities/example.env config --quiet
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 3: Commit and update Linear**

Commit with:

```bash
git commit -m "OPN-273: add Plane pickup preview helper"
```

Update OPN-273 and OPN-264 with commit hash, verification, and remaining live pickup gaps.
