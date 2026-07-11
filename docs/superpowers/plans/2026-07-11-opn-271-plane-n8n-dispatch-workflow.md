# OPN-271 Plane n8n Dispatch Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use test-driven-development for script behavior before implementation. Keep this limited to repo-managed n8n workflow assets; live import/enablement remains an external deployment step.

**Goal:** Add a disabled, importable n8n workflow and sender script for the gateway's `/webhook/plane-openclaw-dispatch` target, so queued Plane webhook events can be forwarded to OpenClaw without hand-writing the n8n automation later.

**Architecture:** The gateway dispatch endpoint sends already-normalized Plane events to n8n. n8n accepts the fixed webhook path, runs a checked-in shell sender, uploads the normalized event to the OpenClaw host over SSH, and invokes a configurable OpenClaw command with `--event-file`. The workflow remains disabled in Git and must be imported/enabled through n8n/Komodo after secrets and SSH mounts are confirmed.

---

### Task 1: Script Contract

**Files:**
- Add: `apps/utilities/n8n/scripts/test-send-plane-openclaw-dispatch.js`
- Add: `apps/utilities/n8n/scripts/send-plane-openclaw-dispatch.sh`

- [x] **Step 1: Write failing sender test**

Assert the script:

- accepts the normalized gateway dispatch payload on stdin,
- uploads only normalized Plane event fields to the OpenClaw host,
- invokes `OPENCLAW_PLANE_DISPATCH_COMMAND --event-file <remote-payload>`,
- preserves `correlation_id`, `delivery_id`, event metadata, actor, and `received_at`.

- [x] **Step 2: Implement sender**

Mirror the existing Linear sender conventions: SSH env defaults, shell quoting, local and remote cleanup, and no secret printing.

### Task 2: n8n Workflow Template

**Files:**
- Add: `apps/utilities/n8n/workflows/plane-openclaw-dispatch.workflow.json`
- Add: `apps/utilities/n8n/scripts/test-plane-openclaw-dispatch-workflow.js`

- [x] **Step 1: Write workflow structure test**

Assert the workflow is disabled, exposes POST path `plane-openclaw-dispatch`, executes `/opt/n8n-scripts/send-plane-openclaw-dispatch.sh`, and returns a small acknowledgement with the correlation ID.

- [x] **Step 2: Add workflow JSON**

Use the existing importable n8n workflow style and keep `active: false`.

### Task 3: Docs, Env, Verification, Linear

**Files:**
- Modify: `apps/utilities/compose.yml`
- Modify: `apps/utilities/example.env`
- Modify: `apps/openclaw-gateway/README.md`
- Modify: `docs/workflow/plane.md`

- [x] **Step 1: Add runtime config docs**

Document `OPENCLAW_PLANE_DISPATCH_COMMAND`, the script mount, workflow import/enablement, and the need to configure real Plane automation actor IDs.

- [x] **Step 2: Verify**

Run the new node tests, existing n8n sender/verifier tests, gateway focused tests, compose config checks, `git diff --check`, and a focused secret scan.

- [x] **Step 3: Commit and update Linear**

Commit this slice and update OPN-271 plus OPN-264 with verification and remaining live deployment gaps.
