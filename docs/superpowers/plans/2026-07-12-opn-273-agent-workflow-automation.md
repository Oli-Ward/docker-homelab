# OPN-273 Agent Workflow Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Plane `Ready for Agent` to OpenClaw/Codex/PR/Plane write-back automation defined in `docs/superpowers/specs/2026-07-12-opn-273-agent-workflow-automation-spec.md`.

**Architecture:** Keep OPN-271 payload uncertainty isolated in one adapter that emits a stable internal command input. The OpenClaw-side workflow owns pickup decisions, route resolution, atomic claims, run state, retry planning, dry-run/live execution, PR/write-back planning, and audit records. Live mutation remains gated until dry-run and smoke evidence pass.

**Tech Stack:** Python OpenClaw command scripts/tests, Plane gateway/n8n normalized events, Git/GitHub command planning, JSONL audit, pytest, shell smoke scripts.

---

## File Structure

- Modify or create OpenClaw command module: `tools/scripts/openclaw_plane_n8n_dispatch.py`
  - Owns event adaptation, pickup classification, routing, claim handling,
    run-state planning, retry planning, outcome recording, write-back planning,
    and CLI entry points.
- Modify or create OpenClaw tests: `tools/tests/test_openclaw_plane_n8n_dispatch.py`
  - Covers every acceptance case in the spec.
- Modify OpenClaw bin wrappers under `tools/bin/`
  - Provides `openclaw-plane-n8n-dispatch`, `openclaw-plane-local-smoke`,
    `openclaw-plane-retry-plan`, `openclaw-plane-claim-outcome`, and
    `openclaw-plane-writeback`.
- Modify OpenClaw docs: `execution/LINEAR_AUTOPICKUP.md` and
  `execution/PLANE_AGENT_WORKFLOW_AUTOMATION_CONTRACT.md`
  - Keeps the operational contract discoverable beside the automation code.
- Modify Docker repo docs only if the n8n/gateway payload contract changes:
  `docs/workflow/plane.md`, `apps/openclaw-gateway/README.md`.

## Task 1: Stable Event Adapter

**Files:**
- Modify: `tools/scripts/openclaw_plane_n8n_dispatch.py`
- Modify: `tools/tests/test_openclaw_plane_n8n_dispatch.py`

- [ ] **Step 1: Add failing adapter tests**

Add tests proving the adapter accepts current OPN-271 aliases and emits the
stable internal fields:

```python
def test_adapt_plane_event_accepts_opn271_aliases():
    event = {
        "delivery_id": "delivery-1",
        "correlation_id": "plane:delivery-1",
        "team": "Openclaw",
        "project_id": "project-1",
        "resource_id": "ticket-1",
        "source_identifier": "OPN-273",
        "state_name": "Ready for Agent",
        "label_names": ["repo:docker", "agent:ready"],
        "sequence_id": 273,
    }

    adapted = adapt_plane_event(event)

    assert adapted.event_delivery_id == "delivery-1"
    assert adapted.plane_workspace_slug == "openclaw"
    assert adapted.plane_project_id == "project-1"
    assert adapted.plane_ticket_id == "ticket-1"
    assert adapted.plane_issue_identifier == "OPN-273"
    assert adapted.ready_revision
    assert adapted.labels == ("repo:docker", "agent:ready")
```

- [ ] **Step 2: Implement the adapter**

Implement `PlaneAutomationEvent` and `adapt_plane_event(raw: dict)`. Default
`plane_workspace_slug` from event workspace fields or the configured local
workspace slug. Derive `ready_revision` from explicit revision, updated-at, or
state/ticket identity. Raise `PermanentInputError("invalid_event")` when
identity, state, or label fields are missing.

- [ ] **Step 3: Verify**

Run:

```bash
pytest -q tools/tests/test_openclaw_plane_n8n_dispatch.py -k adapt_plane_event
python3 -m py_compile tools/scripts/openclaw_plane_n8n_dispatch.py
```

Expected: tests pass and py_compile exits 0.

## Task 2: Pickup Classification And Repository Routing

**Files:**
- Modify: `tools/scripts/openclaw_plane_n8n_dispatch.py`
- Modify: `tools/tests/test_openclaw_plane_n8n_dispatch.py`

- [ ] **Step 1: Add failing classification tests**

Cover ready, not-ready, terminal, suppress labels, missing checklist, missing
repo, multiple repos, and unknown repo:

```python
def test_ready_docker_ticket_classifies_ready():
    decision = classify_pickup(event(labels=("repo:docker",), state_name="Ready for Agent"))
    assert decision.status == "ready"
    assert decision.route.workspace_path == "/home/oli/docker"

def test_missing_repo_label_needs_input():
    decision = classify_pickup(event(labels=(), state_name="Ready for Agent"))
    assert decision.status == "needs_input"
    assert decision.reason == "missing_repo_route"

def test_done_state_is_ignored_before_claim():
    decision = classify_pickup(event(labels=("repo:docker",), state_name="Done", state_type="completed"))
    assert decision.status == "ignored"
    assert decision.reason == "terminal_state"
```

- [ ] **Step 2: Implement classifier and routing table**

Implement deterministic route resolution:

```python
ROUTES = {
    "docker": RepositoryRoute(name="docker", workspace_path="/home/oli/docker", branch_policy="feature_branch"),
    "openclaw": RepositoryRoute(name="openclaw", workspace_path="/home/openclaw/.openclaw/workspace", branch_policy="repo_default"),
}
```

Return `needs_input` instead of guessing when route evidence is missing or
conflicting.

- [ ] **Step 3: Verify**

Run:

```bash
pytest -q tools/tests/test_openclaw_plane_n8n_dispatch.py -k "classify or route"
```

Expected: all focused tests pass.

## Task 3: Atomic Claim Store And Idempotency

**Files:**
- Modify: `tools/scripts/openclaw_plane_n8n_dispatch.py`
- Modify: `tools/tests/test_openclaw_plane_n8n_dispatch.py`

- [ ] **Step 1: Add failing claim tests**

Tests must prove:

- claim ID is `plane:{workspace}:{project}:{ticket}:{ready_revision}`;
- first ready event returns `claimed`;
- duplicate delivery returns `duplicate`;
- duplicate claim does not start another run;
- newer ready revision is blocked while previous claim is active.

- [ ] **Step 2: Implement claim store**

Use the existing local OpenClaw state directory convention. Store one JSON claim
record per claim ID plus a delivery-id index. Use atomic file create or the
existing project locking helper if present. Claim records include event identity,
route, run state, dry-run flag, attempt, timestamps, and latest result.

- [ ] **Step 3: Verify**

Run:

```bash
pytest -q tools/tests/test_openclaw_plane_n8n_dispatch.py -k "claim or duplicate or idempot"
```

Expected: all focused tests pass.

## Task 4: Dry-Run Planning

**Files:**
- Modify: `tools/scripts/openclaw_plane_n8n_dispatch.py`
- Modify: `tools/tests/test_openclaw_plane_n8n_dispatch.py`
- Modify: `tools/bin/openclaw-plane-n8n-dispatch`

- [ ] **Step 1: Add failing dry-run tests**

Assert dry-run JSON includes planned claim, branch, Codex command/session, PR
title, Plane comments/state changes, and audit path. Assert it does not mutate
Plane, Git, GitHub, Docker, n8n, or start Codex by injecting fake writers that
would fail if called.

- [ ] **Step 2: Implement dry-run output**

Default the CLI to dry-run unless `--live` is explicitly passed. Emit compact
JSON:

```json
{
  "status": "claimed",
  "dry_run": true,
  "claim_id": "plane:openclaw:project-1:ticket-1:revision-1",
  "route": {"name": "docker", "workspace_path": "/home/oli/docker"},
  "planned": {
    "branch": "opn-273-agent-workflow-automation",
    "pr_title": "OPN-273: Implement agent workflow automation",
    "plane_state": "In Progress"
  }
}
```

- [ ] **Step 3: Verify**

Run:

```bash
pytest -q tools/tests/test_openclaw_plane_n8n_dispatch.py -k dry_run
tools/bin/openclaw-plane-n8n-dispatch --help
```

Expected: tests pass and help exits 0.

## Task 5: Run-State, Outcome, And Write-Back Planning

**Files:**
- Modify: `tools/scripts/openclaw_plane_n8n_dispatch.py`
- Modify: `tools/tests/test_openclaw_plane_n8n_dispatch.py`
- Modify: `tools/bin/openclaw-plane-claim-outcome`
- Modify: `tools/bin/openclaw-plane-writeback`

- [ ] **Step 1: Add failing run-state tests**

Cover `claimed -> handoff_planned -> running -> changes_ready -> pr_opened ->
completed`, plus `needs_input`, `failed_retryable`, `failed_permanent`, and
`dead_lettered`.

- [ ] **Step 2: Implement outcome recording**

Update claim current state and append audit. Plane write-back planning returns
idempotent operations for comments, state transitions, branch links, PR links,
and verification summaries. Do not apply writes unless the write-back CLI is
called with `--live`.

- [ ] **Step 3: Verify**

Run:

```bash
pytest -q tools/tests/test_openclaw_plane_n8n_dispatch.py -k "outcome or writeback or run_state"
tools/bin/openclaw-plane-claim-outcome --help
tools/bin/openclaw-plane-writeback --help
```

Expected: tests pass and help commands exit 0.

## Task 6: Retry And Dead Letter

**Files:**
- Modify: `tools/scripts/openclaw_plane_n8n_dispatch.py`
- Modify: `tools/tests/test_openclaw_plane_n8n_dispatch.py`
- Modify: `tools/bin/openclaw-plane-retry-plan`

- [ ] **Step 1: Add failing retry tests**

Cover retryable failures scheduling 1m, 5m, 15m, and 1h retries; permanent
failures bypassing retry; exhausted attempts producing dead letter; duplicate
retry not creating another Codex run after `running` or later.

- [ ] **Step 2: Implement retry planner**

Classify transient infrastructure failures separately from implementation
outcomes. Reuse the same claim ID and write a next retry timestamp. Emit
operator replay instructions for dead-lettered claims.

- [ ] **Step 3: Verify**

Run:

```bash
pytest -q tools/tests/test_openclaw_plane_n8n_dispatch.py -k "retry or dead_letter"
tools/bin/openclaw-plane-retry-plan --help
```

Expected: tests pass and help exits 0.

## Task 7: Audit Trail

**Files:**
- Modify: `tools/scripts/openclaw_plane_n8n_dispatch.py`
- Modify: `tools/tests/test_openclaw_plane_n8n_dispatch.py`
- Modify: `execution/LINEAR_AUTOPICKUP.md`
- Modify: `execution/PLANE_AGENT_WORKFLOW_AUTOMATION_CONTRACT.md`

- [ ] **Step 1: Add failing audit tests**

Assert every audit row includes required identity fields from the spec and
excludes raw payload sentinels, tokens, signatures, `.env` values, and runtime
log text.

- [ ] **Step 2: Implement append-only JSONL audit**

Append one record per phase. Include claim, delivery, Plane identity, route,
dry-run, attempt, result, and error code. Redact failure summaries before
writing.

- [ ] **Step 3: Verify**

Run:

```bash
pytest -q tools/tests/test_openclaw_plane_n8n_dispatch.py -k audit
git diff --check -- tools/scripts/openclaw_plane_n8n_dispatch.py tools/tests/test_openclaw_plane_n8n_dispatch.py execution/LINEAR_AUTOPICKUP.md execution/PLANE_AGENT_WORKFLOW_AUTOMATION_CONTRACT.md
```

Expected: tests pass and diff check is clean.

## Task 8: Local Smoke And Live Gate

**Files:**
- Modify: `tools/scripts/openclaw_plane_n8n_dispatch.py`
- Modify: `tools/tests/test_openclaw_plane_n8n_dispatch.py`
- Modify: `tools/bin/openclaw-plane-local-smoke`
- Create or modify: `diagnostics/build-lanes/2026-07-12-opn-273-agent-workflow-smoke.md`

- [ ] **Step 1: Add failing local smoke test**

Smoke must prove claim, duplicate suppression, Codex handoff planning, PR
planning, Plane write-back planning, `needs_input`, and audit phases in a temp
directory.

- [ ] **Step 2: Implement local smoke command**

The command creates temp fixture events, runs dry-run dispatch twice for
duplicate evidence, records one `needs_input` fixture, plans write-back, and
prints a JSON summary with evidence paths.

- [ ] **Step 3: Verify**

Run:

```bash
pytest -q tools/tests/test_openclaw_plane_n8n_dispatch.py -k local_smoke
tools/bin/openclaw-plane-local-smoke --help
tools/bin/openclaw-plane-local-smoke --dry-run
```

Expected: test passes, help exits 0, dry-run smoke exits 0 and prints no
secrets.

- [ ] **Step 4: Live gate checklist**

Before any `--live` run, record in diagnostics:

- non-critical `[SMOKE][OPN-273]` Plane ticket identifier;
- repo route label;
- backup/checkpoint confirmation for affected state stores;
- exact command to run;
- rollback by disabling Plane pickup/n8n trigger and leaving manual Codex
  operation available.

## Task 9: Final Verification

**Files:**
- All touched OpenClaw files.
- Docker repo docs if changed.

- [ ] **Step 1: Run focused verification**

Run:

```bash
pytest -q tools/tests/test_openclaw_plane_n8n_dispatch.py tools/tests/test_openclaw_linear_n8n_handoff.py tools/tests/test_openclaw_linear_autopickup.py tools/tests/test_openclaw_ticket_pickup.py
python3 -m py_compile tools/scripts/openclaw_plane_n8n_dispatch.py
tools/bin/openclaw-plane-n8n-dispatch --help
tools/bin/openclaw-plane-local-smoke --help
tools/bin/openclaw-plane-retry-plan --help
tools/bin/openclaw-plane-claim-outcome --help
tools/bin/openclaw-plane-writeback --help
git diff --check
```

Expected: all commands exit 0. If preflight reports amber because of unrelated
git state, record the amber reason and avoid commits/service changes until the
operator approves.

- [ ] **Step 2: Update Linear**

Comment on `OPN-273` with:

- plan/spec paths;
- verification commands and results;
- dry-run smoke evidence path;
- live smoke status or explicit not-run reason;
- remaining follow-ups, or `None`.
