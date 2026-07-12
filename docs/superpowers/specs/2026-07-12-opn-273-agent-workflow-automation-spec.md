# OPN-273 Agent Workflow Automation Spec

## Goal

Define the Plane to OpenClaw to Codex automation contract for OPN-273. The
only expected future variable is the exact normalized event payload shape from
OPN-271; this spec isolates that variability behind a small event adapter and
keeps pickup, routing, claim, run-state, retry, PR, write-back, and audit
behavior stable.

## Non-Goals

- Do not enable live Plane pickup from this spec alone.
- Do not start Codex sessions, create branches, create PRs, or write to Plane
  without an explicit implementation/smoke step.
- Do not depend on raw Plane webhook payloads outside the OPN-271
  normalization boundary.
- Do not replace Komodo as the deployment source of truth for this Docker repo.

## Inputs

The automation consumes one normalized Plane work-item event from OPN-271. The
adapter must normalize it into this internal command input:

```json
{
  "event_delivery_id": "plane-delivery-id",
  "correlation_id": "plane:plane-delivery-id",
  "plane_workspace_slug": "openclaw",
  "plane_project_id": "project-id",
  "plane_ticket_id": "work-item-id",
  "plane_issue_identifier": "OPN-273",
  "ready_revision": "state-or-updated-at-revision",
  "state_name": "Ready for Agent",
  "state_type": "started",
  "title": "Implement Agent Workflow Automation",
  "labels": ["repo:docker", "agent:builder"],
  "priority": "High",
  "source": "plane",
  "actor_id": "plane-user-id"
}
```

The adapter may accept aliases such as `delivery_id`, `source_identifier`,
`identifier`, `resource_id`, `project_id`, `label_names`, and `sequence_id`.
All downstream code must consume only the internal command input.

## Pickup Criteria

A ticket is eligible only when all required conditions are true:

- Resource is a Plane issue/work item, not a comment, project, label, or user
  event.
- Current state name is exactly `Ready for Agent`.
- State type is not terminal. Terminal state names are `Done`, `Canceled`, and
  `Duplicate`; terminal state types are `completed`, `canceled`, and
  `duplicate`.
- No suppressing labels are present: `agent:hold`, `manual`, `no-agent`,
  `needs-decision`, `needs-research`, or any `blocked:*` label.
- Agent-ready checklist is present in the ticket body or metadata: goal,
  repository/system boundary, likely files or service area when known, safety
  constraints, verification, acceptance criteria, dependency notes, and
  rollback/deployment notes when applicable.
- A repository route can be resolved exactly.
- The event is not authored by a configured automation actor.
- No active claim exists for the same ticket and ready revision.

If eligibility fails before a claim is created, return `ignored` for terminal,
not-ready, or suppressed events, and return `needs_input` for missing checklist
or ambiguous routing. Do not start Codex.

## Repository Routing

Routing is deterministic and conservative:

1. Prefer a single `repo:<name>` label.
2. If no repo label exists, use an explicit ticket metadata field such as
   `repository`, `repo`, or `implementation_repo` after OPN-271/272 exposes one.
3. If still unresolved, infer only from a maintained routing table, not from
   free-form title text.
4. If multiple repo labels or conflicting metadata exist, return
   `needs_input`.

Initial routing table:

| Route | Workspace path | Branch policy |
| --- | --- | --- |
| `repo:docker` | `/home/oli/docker` | Create feature branch unless explicitly running docs-only dry-run. |
| `repo:openclaw` | `/home/openclaw/.openclaw/workspace` | Follow OpenClaw repo policy; current default is long-lived `dev` unless isolation is requested. |

Unknown routes produce a Plane `Needs Input` intent with the missing or
ambiguous route details.

## Claim Semantics

The claim is the idempotency boundary for work execution.

- Claim ID: `plane:{workspace}:{project_id}:{ticket_id}:{ready_revision}`.
- Event ID: the OPN-271 delivery ID.
- A claim can be `claimed`, `duplicate`, `released`, `completed`,
  `failed_retryable`, `failed_permanent`, or `dead_lettered`.
- Creating a claim is atomic. If the same claim ID already exists in an active
  or terminal state, the command returns `duplicate` and does not start Codex.
- A newer `ready_revision` for the same ticket may create a new claim only when
  the previous claim is terminal or explicitly released.
- Claims persist enough metadata to replay audit and write-back without
  rereading raw webhook payloads.

## Branch, Commit, And PR Naming

For repositories that use per-ticket branches:

- Branch: `opn-273-agent-workflow-automation`
- Commit subject: `OPN-273: <imperative summary>`
- PR title: `OPN-273: <human-readable implementation summary>`

Branch names must be lowercase, ASCII, slash-free unless the repo already uses
a namespace convention, and capped at a practical length. If a repo uses a
long-lived branch, preserve the ticket identifier in commit subjects and PR
titles instead.

## Run-State Model

The run-state model is append-only in audit, with a single current state on the
claim:

| State | Meaning | Plane write-back intent |
| --- | --- | --- |
| `received` | Event accepted by OpenClaw command. | None. |
| `ignored` | Not eligible and no human action needed. | Optional comment only in dry-run diagnostics. |
| `needs_input` | Human decision required before execution. | Move or propose move to `Needs Input`; add actionable comment. |
| `claimed` | Atomic claim created. | Comment with claim, route, branch intent; then move to `In Progress`. |
| `handoff_planned` | Codex command/session plan built. | Progress comment in dry-run only. |
| `running` | Codex execution started. | Progress comment if live. |
| `changes_ready` | Work produced commits or a patch. | Link branch/commit. |
| `pr_opened` | PR exists. | Link PR and move/propose move to `In Review`. |
| `completed` | Acceptance criteria and verification passed. | Comment with verification; move/propose move to `Done` only when allowed. |
| `failed_retryable` | Transient failure, retry scheduled. | Comment only when useful; keep `In Progress` or automation state. |
| `failed_permanent` | Non-retryable failure. | Move/propose move to `Blocked` or `Needs Input` with next action. |
| `dead_lettered` | Retry budget exhausted. | Move/propose move to `Blocked`; add evidence and owner/action. |

State transitions must be monotonic except explicit release back to
`Ready for Agent` after a human or operator action.

## Retries

Retry only transient failures:

- Plane/gateway/n8n 429 or 5xx responses.
- Temporary SSH/network errors.
- Lock contention or claim store unavailable.
- GitHub rate limit or temporary service outage.

Do not retry permanent failures:

- Missing or ambiguous repo route.
- Missing checklist.
- Invalid normalized event after adapter parsing.
- Authentication/permission failure until credentials are fixed.
- Test failures or code review failures. Those are implementation outcomes,
  not transport retries.

Backoff schedule: 1 minute, 5 minutes, 15 minutes, 1 hour, then dead letter.
Retries reuse the same claim ID and never create another Codex run after a run
has reached `running`, `changes_ready`, `pr_opened`, or `completed` unless an
operator explicitly requeues the claim.

## Idempotency

Idempotency keys:

- Delivery idempotency: `event_delivery_id`.
- Work idempotency: claim ID.
- Plane write-back idempotency: `claim_id + writeback_phase`.
- PR link idempotency: `claim_id + pr_url`.

Duplicate deliveries can update audit with `duplicate_event` but must not
start another claim. Duplicate write-back attempts must be no-ops if the same
status/comment/link has already been recorded.

## Failure Handling

Failure handling always produces an actionable outcome:

- `needs_input`: write the missing decision in plain language and include the
  exact fields/labels needed.
- `blocked`: record dependency, missing access, external outage, or unsafe
  precondition with evidence.
- `failed_retryable`: record next retry timestamp and retry attempt.
- `dead_lettered`: record exhausted attempts, last error class, and operator
  replay command.

Never mark a ticket Done after failure handling. Never hide a partial branch or
PR; link it and explain what remains.

## Dry-Run Mode

Dry-run is the default for initial rollout.

Dry-run may:

- Parse and classify the event.
- Resolve repository route.
- Plan claim creation.
- Plan branch, Codex command, PR title, Plane comments, and Plane state changes.
- Write local audit evidence.

Dry-run must not:

- Create or mutate Plane tickets.
- Start Codex.
- Create branches, commits, or PRs.
- Push to GitHub.
- Mutate Docker, Komodo, n8n, or live services.

Dry-run output must be JSON and include `status`, `decision`, `claim_id`,
`route`, planned operations, and audit path. It must not include secrets or raw
payloads.

## Audit Trail

Audit is JSONL, append-only, and secret-free. Each record includes:

- `timestamp`
- `phase`
- `claim_id`
- `event_delivery_id`
- `correlation_id`
- `plane_workspace_slug`
- `plane_project_id`
- `plane_ticket_id`
- `plane_issue_identifier`
- `ready_revision`
- `route`
- `run_state`
- `dry_run`
- `attempt`
- `result`
- `error_code` when applicable

Audit records may include branch names, commit hashes, PR URLs, verification
commands, and redacted failure summaries. They must not include tokens, raw
webhook bodies, `.env` values, cookies, private keys, or runtime logs with
credentials.

## Acceptance Tests

The implementation is accepted when tests prove:

- Ready ticket with `repo:docker` produces `claimed`, route `/home/oli/docker`,
  branch `opn-273-agent-workflow-automation`, and PR title prefix `OPN-273:`.
- Not-ready, terminal, suppress-label, and automation-actor events are ignored
  without claims.
- Missing repo, multiple repo labels, and missing checklist produce
  `needs_input`.
- Duplicate delivery does not create a second claim.
- Duplicate claim for the same `ready_revision` does not start another run.
- New `ready_revision` can be claimed only after prior claim is terminal or
  released.
- Retryable downstream failures schedule retry with capped backoff.
- Permanent failures produce `Needs Input` or `Blocked` write-back intent.
- Dry-run plans all operations without mutating Plane, Git, GitHub, Docker, or
  n8n.
- Live-mode happy path records claim, starts Codex in the resolved repo, links
  branch/PR, writes Plane comments, and reaches `In Review` or `Done` according
  to the configured completion policy.
- Audit JSONL contains required identity fields and excludes raw payloads and
  secrets.

## Rollout

1. Keep live pickup disabled.
2. Run local dry-run tests against fixtures from OPN-271.
3. Run a local smoke that proves claim, duplicate, handoff planning, PR
   planning, write-back planning, and audit evidence.
4. Run a live dry-run against a non-critical `[SMOKE][OPN-273]` Plane ticket.
5. Enable one guarded live pickup path for a single repo route.
6. Keep old Linear/manual operation available until Plane pickup proves stable.
7. Disable old Linear pickup only after successful live evidence covers normal
   flow, duplicate replay, retry/dead-letter, and rollback.
