# OPN-273 Plane Dispatch Preview Gate Implementation Plan

> **Archived 2026-07-12:** This completed prerequisite slice is no longer the active OPN-273 plan. Linear OPN-273 still owns the full Ready for Agent -> OpenClaw -> Codex -> PR -> Plane write-back workflow, including state transitions, retries, PR links, and failure updates. Keep this file as historical implementation evidence.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gate the repo-managed Plane n8n dispatch path with the read-only pickup preview so non-ready events do not SSH to OpenClaw, while preserving safe Plane metadata needed for routing.

**Architecture:** Keep the workflow disabled by default. The n8n workflow should pass all normalized allowlisted Plane event fields to the sender. The sender should normalize input, run `plane-agent-pickup-preview.js`, return the preview decision for `ignored` or `needs_input`, and only require SSH/OpenClaw settings when the decision is `ready`.

**Tech Stack:** n8n workflow JSON, POSIX shell sender script, Node.js helper/test scripts, Docker Compose config validation.

## Global Constraints

- Do not import, enable, or mutate live n8n workflows.
- Do not run Docker deploy/restart/pull/up/down commands.
- Do not read or print real `.env` files or secrets.
- Keep the workflow artifact `active: false`.
- The preview gate must not call Plane, GitHub, Docker, OpenClaw, SSH, or live n8n for non-ready events.

---

### Task 1: Sender Preview Gate Tests

**Files:**
- Modify: `apps/utilities/n8n/scripts/test-send-plane-openclaw-dispatch.js`

**Interfaces:**
- Consumes: `apps/utilities/n8n/scripts/send-plane-openclaw-dispatch.sh`
- Consumes: `apps/utilities/n8n/scripts/plane-agent-pickup-preview.js`
- Produces: tests proving the sender exits locally for ignored/needs-input events and preserves the existing ready SSH behavior.

- [x] **Step 1: Add a failing non-ready test**

Add a second invocation in `test-send-plane-openclaw-dispatch.js` that sends a `state_name: "Todo"` issue without setting `OPENCLAW_SSH_HOST`. Assert exit code `0`, stdout JSON has `decision: "ignored"` and `reason: "not_ready_for_agent"`, and no fake SSH payload file exists.

- [x] **Step 2: Add a failing missing-repo test**

Add a third invocation that sends `state_name: "Ready for Agent"` with no `repo:<name>` label and no `OPENCLAW_SSH_HOST`. Assert exit code `0`, stdout JSON has `decision: "needs_input"` and `reason: "missing_repo_label"`, and no fake SSH payload file exists.

- [x] **Step 3: Run the test and verify red**

Run:

```bash
node apps/utilities/n8n/scripts/test-send-plane-openclaw-dispatch.js
```

Expected: fail before implementation because the sender requires `OPENCLAW_SSH_HOST` before previewing events.

### Task 2: Sender Preview Gate Implementation

**Files:**
- Modify: `apps/utilities/n8n/scripts/send-plane-openclaw-dispatch.sh`

**Interfaces:**
- Produces: sender behavior where `ready` events keep current SSH handoff and non-ready events return preview JSON without SSH requirements.

- [x] **Step 1: Move SSH env validation after preview**

Keep `NODE_BIN` available before normalization. Move `OPENCLAW_SSH_HOST`, `OPENCLAW_SSH_USER`, `OPENCLAW_SSH_PORT`, `OPENCLAW_SSH_KEY_PATH`, `OPENCLAW_WORKSPACE`, and `OPENCLAW_PLANE_DISPATCH_COMMAND` initialization until after the preview decision says `ready`.

- [x] **Step 2: Run preview after normalization**

After writing the normalized payload file, run:

```sh
preview_file=$(mktemp)
"$NODE_BIN" "$(dirname "$0")/plane-agent-pickup-preview.js" "$payload_file" > "$preview_file"
decision=$("$NODE_BIN" - "$preview_file" <<'NODE'
const fs = require("fs");
const preview = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
process.stdout.write(preview.decision || "");
NODE
)
```

If `decision` is not `ready`, print the preview JSON and exit `0`.

- [x] **Step 3: Verify sender tests pass**

Run:

```bash
node apps/utilities/n8n/scripts/test-send-plane-openclaw-dispatch.js
```

Expected: pass.

### Task 3: Workflow Metadata Pass-Through

**Files:**
- Modify: `apps/utilities/n8n/workflows/plane-openclaw-dispatch.workflow.json`
- Modify: `apps/utilities/n8n/scripts/test-plane-openclaw-dispatch-workflow.js`

**Interfaces:**
- Produces: disabled workflow artifact that passes `project_id`, `sequence_id`, `name`, `state_id`, `state_name`, `priority`, and `label_names` from webhook body into the sender payload.

- [x] **Step 1: Add failing workflow assertions**

Update `test-plane-openclaw-dispatch-workflow.js` to assert the `Build Plane Dispatch Payload` node has assignments for:

- `project_id`
- `sequence_id`
- `name`
- `state_id`
- `state_name`
- `priority`
- `label_names`

Run:

```bash
node apps/utilities/n8n/scripts/test-plane-openclaw-dispatch-workflow.js
```

Expected: fail before implementation because the workflow currently strips these fields.

- [x] **Step 2: Add workflow assignments**

Add the missing assignments to the `Build Plane Dispatch Payload` set node. Use body expressions that mirror the normalized gateway event field names and keep the workflow `active: false`.

- [x] **Step 3: Verify workflow test passes**

Run:

```bash
node apps/utilities/n8n/scripts/test-plane-openclaw-dispatch-workflow.js
```

Expected: pass.

### Task 4: Docs, Verification, Commit, Linear

**Files:**
- Modify: `apps/openclaw-gateway/README.md`
- Modify: `docs/workflow/plane.md`
- Modify: `docs/superpowers/plans/2026-07-11-opn-273-plane-dispatch-preview-gate.md`

**Interfaces:**
- Produces: documented safe behavior and final Linear checkpoint.

- [x] **Step 1: Document preview gate**

Document that the disabled n8n dispatch sender now previews normalized events first and only SSHes for `ready` decisions. Clarify that `ignored` and `needs_input` events are acknowledged locally with a decision JSON and no OpenClaw handoff.

- [x] **Step 2: Run verification**

Run:

```bash
node apps/utilities/n8n/scripts/test-plane-agent-pickup-preview.js
node apps/utilities/n8n/scripts/test-send-plane-openclaw-dispatch.js
node apps/utilities/n8n/scripts/test-plane-openclaw-dispatch-workflow.js
docker compose -f apps/utilities/compose.yml --env-file apps/utilities/example.env config --quiet
git diff --check
```

Run a focused changed-file secret scan.

- [ ] **Step 3: Commit and update Linear**

Commit with:

```bash
git commit -m "OPN-273: gate Plane dispatch with pickup preview"
```

Update OPN-273 and OPN-264 with commit hash, verification, and remaining live gaps.
