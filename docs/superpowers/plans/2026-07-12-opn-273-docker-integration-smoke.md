# OPN-273 Docker Integration Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the Docker-side Plane/OpenClaw integration checkpoint, commit validated repo changes, run an OPN-273 live dry-run smoke, and record evidence.

**Architecture:** Keep durable configuration in this Docker Compose repo, use live Docker/Komodo state only as diagnostic evidence, and avoid direct Compose lifecycle mutations. The smoke should exercise the existing gateway/n8n/OpenClaw path with a non-critical Plane event and document any remaining cutover blockers.

**Tech Stack:** Docker Compose config validation, pytest, Node script tests, git, live read-only Docker inspection plus approved smoke commands, Linear comments.

---

### Task 1: Validate And Commit Current Docker Changes

**Files:**
- Modify: `apps/openclaw-gateway/README.md`
- Modify: `apps/openclaw-gateway/compose.yml`
- Modify: `apps/openclaw-gateway/example.env`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_plane_sdk/client.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_plane_client.py`
- Modify: `apps/plane/README.md`
- Modify: `apps/plane/compose.yml`
- Modify: `apps/plane/example.env`
- Add: `diagnostics/build-lanes/2026-07-12-plane-cutover-readiness.md`
- Add: `diagnostics/build-lanes/2026-07-12-linear-plane-missing-active-team-issues.tsv`

- [x] **Step 1: Run focused tests and config checks**

Run:

```bash
cd apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_plane_client.py -q
cd /home/oli/docker
docker compose -f apps/openclaw-gateway/compose.yml --env-file apps/openclaw-gateway/example.env config --quiet
docker compose -f apps/plane/compose.yml --env-file apps/plane/example.env config --quiet
git diff --check
```

- [x] **Step 2: Commit only scoped files**

Commit the validated checkpoint with:

```bash
git add apps/openclaw-gateway/README.md apps/openclaw-gateway/compose.yml apps/openclaw-gateway/example.env apps/openclaw-gateway/openclaw-gateway/openclaw_plane_sdk/client.py apps/openclaw-gateway/openclaw-gateway/tests/test_plane_client.py apps/plane/README.md apps/plane/compose.yml apps/plane/example.env diagnostics/build-lanes/2026-07-12-plane-cutover-readiness.md diagnostics/build-lanes/2026-07-12-linear-plane-missing-active-team-issues.tsv docs/superpowers/plans/2026-07-12-opn-273-docker-integration-smoke.md
git commit -m "OPN-273: record Plane integration readiness"
```

### Task 2: Run OPN-273 Live Dry-Run Smoke

**Files:**
- Modify: `diagnostics/build-lanes/2026-07-12-plane-cutover-readiness.md`

- [x] **Step 1: Inspect live route and env presence without printing secrets**

Check gateway, n8n, and OpenClaw dispatch readiness using Docker inspection and redacted env-presence checks only.

- [x] **Step 2: Exercise the gateway to n8n to OpenClaw path**

Use an existing non-critical Plane dispatch event or create a synthetic signed Plane-format event that is `Ready for Agent` and has a `repo:<name>` label. Verify the event reaches n8n, SSHes to OpenClaw, and produces a dry-run or claim result without starting a real Codex run.

Result: gateway ingress accepted and queued a synthetic event, but full gateway dispatch exposed a contract gap. The downstream live n8n sender reached OpenClaw and returned `OPN-273: ready: dry-run` after the payload included `team` and `source_identifier`.

- [x] **Step 3: Verify duplicate suppression**

Repeat the same delivery or claim key and verify OpenClaw reports duplicate behavior rather than creating a second active claim.

Result: direct OpenClaw `--claim --json` returned `status: claimed` on first run and `status: duplicate` on the second run for the same claim key.

### Task 3: Record Evidence And Update Linear

**Files:**
- Modify: `diagnostics/build-lanes/2026-07-12-plane-cutover-readiness.md`

- [x] **Step 1: Append smoke evidence**

Record timestamp, commands, redacted evidence, outcome, and remaining blockers in the readiness report.

- [x] **Step 2: Commit the smoke evidence**

Run focused doc checks, then commit with:

```bash
git add diagnostics/build-lanes/2026-07-12-plane-cutover-readiness.md
git commit -m "OPN-273: record Plane pickup smoke evidence"
```

- [x] **Step 3: Update Linear**

Comment on OPN-273 with the commit hashes, verification run, smoke result, and remaining follow-ups.
