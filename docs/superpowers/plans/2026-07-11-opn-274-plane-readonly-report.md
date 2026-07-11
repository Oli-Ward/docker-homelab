# OPN-274 Plane Read-Only n8n Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first repo-managed read-only n8n Plane automation template: a disabled workflow and tested script that summarizes Plane work items through the OpenClaw gateway without writing to Plane.

**Architecture:** n8n runs a checked-in Node script from `/opt/n8n-scripts`. The script calls the authenticated gateway Plane endpoints using `MEDIA_GATEWAY_URL`, `MEDIA_GATEWAY_TOKEN`, and `PLANE_REPORT_PROJECT_ID`, fetches project states and work items, and emits a compact JSON report. This first automation is deliberately read-only and has no Slack/GitHub side effects.

**Tech Stack:** n8n workflow JSON, Node.js built-ins, gateway `/v1/workflow/plane` API, Docker Compose env placeholders, existing n8n script test pattern.

---

### Task 1: Report Script

**Files:**
- Add: `apps/utilities/n8n/scripts/plane-workflow-report.js`
- Add: `apps/utilities/n8n/scripts/test-plane-workflow-report.js`

- [x] **Step 1: Write failing report script test**

Test `buildPlaneWorkflowReport()` with a fake fetch implementation. It should request states and work items from the gateway, send `Authorization: Bearer <token>`, map state IDs to state names, count items by state and priority, and return top work item summaries without raw Plane payloads.

Run:

```bash
node apps/utilities/n8n/scripts/test-plane-workflow-report.js
```

Expected: fail because `plane-workflow-report.js` does not exist.

- [x] **Step 2: Implement report script**

Implement exported helpers:

- `buildPlaneWorkflowReport(options)`
- `summarizeWorkItems(workItems, statesById)`

The CLI mode should read env vars and print JSON. Required env vars:

- `MEDIA_GATEWAY_URL`
- `MEDIA_GATEWAY_TOKEN`
- `PLANE_REPORT_PROJECT_ID`

Optional env var:

- `PLANE_REPORT_LIMIT`, default `100`

### Task 2: Workflow Template

**Files:**
- Add: `apps/utilities/n8n/workflows/plane-workflow-report.workflow.json`
- Add: `apps/utilities/n8n/scripts/test-plane-workflow-report-workflow.js`

- [x] **Step 1: Write failing workflow structure test**

Assert the workflow is disabled, has a schedule trigger, executes `/opt/n8n-scripts/plane-workflow-report.js`, and returns/keeps the JSON report inside n8n execution output.

- [x] **Step 2: Add disabled n8n workflow**

Create a disabled importable workflow named `plane-workflow-report` with a schedule trigger and execute-command node.

### Task 3: Env, Docs, Verification, Linear

**Files:**
- Modify: `apps/utilities/compose.yml`
- Modify: `apps/utilities/example.env`
- Modify: `docs/workflow/plane.md`
- Modify: `README.md`

- [x] **Step 1: Add runtime env placeholders**

Expose `MEDIA_GATEWAY_URL`, `MEDIA_GATEWAY_TOKEN`, `PLANE_REPORT_PROJECT_ID`, and `PLANE_REPORT_LIMIT` to n8n with safe example placeholders.

- [x] **Step 2: Document workflow**

Document that this is a disabled read-only report automation and live completion still requires importing/enabling it in n8n and configuring real gateway credentials outside Git.

- [x] **Step 3: Verify**

Run:

```bash
node apps/utilities/n8n/scripts/test-plane-workflow-report.js
node apps/utilities/n8n/scripts/test-plane-workflow-report-workflow.js
docker compose -f apps/utilities/compose.yml --env-file apps/utilities/example.env config --quiet
git diff --check
```

Expected: all commands exit 0.

- [x] **Step 4: Commit and update Linear**

Commit with:

```bash
git commit -m "OPN-274: add Plane read-only n8n report"
```

Update OPN-274 and OPN-264 with commit hash, verification, and remaining live enablement gaps.
