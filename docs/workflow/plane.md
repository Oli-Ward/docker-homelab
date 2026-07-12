# Plane Workflow Contract

This is the shared workflow contract for moving OpenClaw issue tracking from
Linear to Plane. It exists so migration scripts, OpenClaw, Codex/ChatGPT tools,
gateway routes, agent pickup, and n8n automations use the same state, label,
priority, and metadata meanings.

## Scope

This document covers:

- Plane states and allowed transitions.
- State owners and automation meanings.
- Linear-to-Plane status, priority, and label mappings.
- Required content for agent-ready tickets.
- Ticket template structure.
- Changes that are safe before import versus changes that belong in the
  migration/cutover window.

It does not implement the migration, Plane webhooks, Codex tools, or n8n
automations. Those remain in the OPN-269 through OPN-274 tickets.

## State Model

Create these Plane states before importing broad Linear data.

| Plane state | Definition | Owner | Automation meaning |
| --- | --- | --- | --- |
| Backlog | Captured work that is not committed for near-term execution. Requirements may be incomplete. | Human/operator | No pickup. Can be searched and triaged only. |
| Todo | Accepted work that is intentionally queued, but not ready for automated implementation. | Human/operator | No pickup. Eligible for grooming and dependency checks. |
| Ready for Agent | Work has enough context and is explicitly approved for an agent to pick up. | Human/operator, after review | Primary pickup gate for OpenClaw/Codex agents. |
| In Progress | Work is actively being implemented or investigated. | Human, agent, or automation that claimed the item | Agent writes progress comments and may link branches/commits. |
| Needs Input | Work is paused for a user decision, missing requirement, or external answer that an agent cannot infer safely. | Human/operator | Suppress automatic pickup until returned to Ready for Agent or Todo. |
| Blocked | Work is stopped by a concrete dependency, missing access, failed external system, or unsafe precondition. | Human/operator, agent may propose with evidence | Suppress pickup; blocked reason must be recorded. |
| In Review | Implementation or document change is ready for review, deploy approval, or manual verification. | Human/operator or reviewer agent | Agents may add verification evidence but must not mark Done without approval rules. |
| Done | Acceptance criteria are met and verification evidence is recorded. | Human/operator or approved automation | Terminal successful state. |
| Canceled | Work is intentionally abandoned and should not be picked up. | Human/operator | Terminal non-success state. |
| Duplicate | Work is represented by another ticket. | Human/operator or migration cleanup | Terminal duplicate state; link the canonical ticket. |

## Allowed Transitions

| From | Allowed next states | Notes |
| --- | --- | --- |
| Backlog | Todo, Ready for Agent, Canceled, Duplicate | Direct Backlog to Ready for Agent is allowed only when the ticket already meets the agent-ready checklist. |
| Todo | Ready for Agent, Needs Input, Blocked, Canceled, Duplicate, Backlog | Use Todo for accepted work that still needs grooming before agents. |
| Ready for Agent | In Progress, Needs Input, Blocked, Todo, Canceled, Duplicate | Agent pickup moves Ready for Agent to In Progress only after it has recorded a pickup/progress comment. |
| In Progress | In Review, Needs Input, Blocked, Ready for Agent, Canceled | Return to Ready for Agent only when work was released back to the queue with current context. |
| Needs Input | Todo, Ready for Agent, Blocked, Canceled | The resolving comment must state the decision or missing input received. |
| Blocked | Todo, Ready for Agent, In Progress, Canceled | The resolving comment must state what changed and why the blocker is gone. |
| In Review | Done, In Progress, Needs Input, Blocked | Done requires fresh verification evidence; failed review returns to In Progress with comments. |
| Done | In Progress | Reopen only for confirmed regression or incomplete acceptance criteria; create a follow-up if the new work is separate. |
| Canceled | Backlog, Todo | Reopen only if the cancellation reason no longer applies. |
| Duplicate | Backlog, Todo | Reopen only if the canonical duplicate was wrong. |

## Linear Status Mapping

The current Linear Openclaw workspace has these statuses:

| Linear status | Plane state | Migration note |
| --- | --- | --- |
| Backlog | Backlog | Preserve directly. |
| Todo | Todo | Preserve directly. |
| In Progress | In Progress | Preserve directly. |
| Blocked | Blocked | Preserve directly and keep blocked labels if present. |
| In Review | In Review | Preserve directly. |
| Done | Done | Preserve completion timestamps where import tooling supports them. |
| Canceled | Canceled | Preserve directly. |
| Duplicate | Duplicate | Preserve duplicate relation/link where import tooling supports it. |

`Ready for Agent` is new in Plane. During migration, map Linear issues with
the `agent:ready` label to `Ready for Agent` only if they are not terminal and
are not suppressed by a hold/risk label. Otherwise preserve their Linear status
and keep `agent:ready` as a label for audit.

## Priority Mapping

| Linear priority | Plane priority | Meaning |
| --- | --- | --- |
| Urgent | Urgent | Time-sensitive or blocks major migration/cutover progress. |
| High | High | Important near-term implementation or dependency work. |
| Medium | Medium | Normal planned work. |
| Low | Low | Useful but not driving current milestones. |
| No priority | None | Captured but not ranked. |

Do not infer urgency from labels alone. If a migrated issue has conflicting
priority evidence, preserve the Linear priority and add a migration discrepancy
note.

## Label Taxonomy

Keep labels namespaced. Do not create ad hoc synonyms during import.

| Namespace | Meaning | Examples | Automation use |
| --- | --- | --- | --- |
| `agent:*` | Agent routing and role gates. | `agent:ready`, `agent:builder`, `agent:review`, `agent:operator` | Pickup, reviewer routing, role selection. |
| `area:*` | Product/domain area. | `area:workflow`, `area:media`, `area:homelab`, `area:security` | Reporting, dashboards, routing. |
| `host:*` | Host or runtime boundary. | `host:media`, `host:openclaw`, `host:proxmox`, `host:media-homelab` | Deployment checklist and safety boundaries. |
| `tag:*` | Topic, technology, or integration marker. | `tag:plane`, `tag:linear`, `tag:n8n`, `tag:webhooks`, `tag:docker` | Search, migration grouping, optional automation filters. |
| `type:*` | Work class. | `type:infra`, `type:security`, `type:connector`, `type:skill` | Template selection and reporting. |
| `blocked:*` | Blocker class. | `blocked:dependency`, `blocked:technical`, `blocked:external`, `blocked:oli` | Blocked-state summaries and escalation. |
| `context:*` | Scheduling or intent context. | `context:now`, `context:later`, `context:experiment`, `context:recurring` | Prioritization and weekly review. |

### Pickup Labels

Use `Ready for Agent` as the durable Plane pickup state. Keep `agent:ready` as:

- a migration marker for Linear-originated tickets,
- a backward-compatible filter while old Linear/n8n pickup code exists,
- an optional secondary guard for high-risk automated pickup.

Suppress automated pickup when any of these labels are present:

- `agent:hold`
- `manual`
- `no-agent`
- `blocked:*`
- `needs-decision`
- `needs-research`

If these labels do not exist during migration, create them before import or
map equivalent source labels to them in the migration discrepancy report.

## Required Agent-Ready Checklist

A ticket may enter `Ready for Agent` only when it includes:

- Clear goal and expected outcome.
- Repository or system boundary, such as `/home/oli/docker`,
  OpenClaw workspace, Plane UI, NPM, Authentik, Komodo, or n8n.
- Files, stack, service, or docs likely to change when known.
- Explicit safety constraints, including whether live Docker mutation is
  allowed. Default for this repo is no direct `docker compose up/down/pull`.
- Required verification commands or manual checks.
- External UI/deployment checklist when repo edits alone are insufficient.
- Secret handling rules when credentials, tokens, webhooks, or API keys are
  involved.
- Acceptance criteria specific enough for an agent to prove completion.
- Dependency links when another ticket must land first.

If any item is missing, use `Todo`, `Needs Input`, or `Blocked`, not
`Ready for Agent`.

## Ticket Templates

### Epic

Use for umbrella coordination only.

Required sections:

- Purpose.
- Child tickets table with priority, responsibility, and dependencies.
- Architecture direction.
- Epic acceptance criteria.
- Cutover checklist if source-of-truth or production behavior changes.
- Notes and sign-off requirements.

Epics should not be agent-pickup targets unless the work is explicitly to
update the epic record itself.

### Implementation Ticket

Required sections:

- Goal.
- Scope.
- Implementation plan.
- Acceptance criteria.
- Testing and rollback.
- Dependencies.
- Future enhancements.

Implementation tickets can enter `Ready for Agent` when the checklist above is
complete.

### Investigation Ticket

Required sections:

- Question or decision to resolve.
- Evidence to gather.
- Commands or systems that may be inspected.
- Safety boundaries.
- Decision record format.
- Follow-up ticket criteria.

Investigations can enter `Ready for Agent` when the evidence-gathering boundary
is clear and no unsafe access is required.

### Bug Ticket

Required sections:

- Observed behavior.
- Expected behavior.
- Reproduction or evidence.
- Suspected scope.
- Regression test expectation.
- Rollback or mitigation path.

Bug tickets require a failing test, captured reproduction, or concrete runtime
evidence before Done.

### Automation Ticket

Required sections:

- Trigger.
- Input payload.
- Validation/authentication policy.
- Dedupe/idempotency key.
- Retry and failure behavior.
- Loop-prevention rule.
- Output/write-back behavior.
- Logs and correlation ID requirements.
- Disable/rollback procedure.

Automation tickets must not enter `Ready for Agent` until their event shape and
secret boundary are explicit.

## Automation Rules

### Agent Pickup

1. Find tickets in `Ready for Agent`.
2. Suppress tickets with hold/risk labels.
3. Add a pickup comment with actor, repository, and intended first step.
4. Move the ticket to `In Progress`.
5. Link branch/commit/PR or record why there is no branch.
6. Write progress comments after meaningful repo or external-state changes.

### Write-Back

Agents and gateway/n8n automations may write:

- progress comments,
- verification evidence,
- branch/commit/PR links,
- state transitions explicitly allowed above.

They must not write:

- secrets,
- raw webhook payloads containing credentials,
- runtime logs with tokens,
- Done transitions without fresh verification evidence.

### Loop Prevention

Plane webhook consumers must ignore or suppress events that were created by:

- the gateway service account,
- OpenClaw write-back automation,
- Codex/ChatGPT integration users,
- n8n automations acting on an event they originally processed.

Use actor identity plus a correlation ID or idempotency key. For migration-era
compatibility, preserve source event IDs such as `linear-delivery-id` or
`plane-webhook-id` in comments/logs where safe.

The OpenClaw gateway webhook ingress uses `X-Plane-Delivery` as its first
idempotency key and derives `plane:<delivery-id>` as the correlation ID for
the acknowledgement, queue record, and structured log fields. It stores only a
normalized delivery record in the local gateway queue; raw Plane payloads and
credential-bearing headers must not be persisted.

The normalized queued/dispatch event may include this allowlisted work-item
metadata when Plane provides it:

```json
{
  "source": "plane",
  "event": "issue",
  "action": "update",
  "correlation_id": "plane:delivery-id",
  "delivery_id": "delivery-id",
  "resource_id": "work-item-uuid",
  "webhook_id": "webhook-uuid",
  "actor_id": "plane-user-uuid",
  "team": "Openclaw",
  "project_id": "project-uuid",
  "source_identifier": "OPN-273",
  "sequence_id": 273,
  "name": "Ready for agent",
  "state_id": "state-uuid",
  "state_name": "Ready for Agent",
  "priority": "high",
  "label_names": ["agent:ready", "repo:docker"]
}
```

Do not add descriptions, comments, raw payload fragments, webhook signatures,
API keys, or arbitrary nested Plane objects to the normalized event. Downstream
agent pickup can use the allowlisted `state_name`, `label_names`, `team`,
`project_id`, `source_identifier`, and sequence metadata for dry-run eligibility
decisions.

The repo-managed pickup preview helper is:

- script: `apps/utilities/n8n/scripts/plane-agent-pickup-preview.js`
- input: one normalized Plane dispatch event from stdin or a JSON file path
- output: a compact JSON decision with `ignored`, `needs_input`, or `ready`

The helper is read-only and is not live-enabled by default. It treats only
`event: "issue"` records in `Ready for Agent` as pickup candidates, requires a
`repo:<name>` label before returning `ready`, and copies only allowlisted
metadata to its output. It does not start OpenClaw/Codex, write to Plane, call
GitHub, SSH anywhere, or mutate n8n state.

The repo-managed n8n dispatch sender runs this preview before any OpenClaw SSH
handoff. `ignored` and `needs_input` decisions return the compact preview JSON
locally and do not require OpenClaw SSH configuration. Only `ready` decisions
continue to `OPENCLAW_PLANE_DISPATCH_COMMAND`.

Configure `PLANE_WEBHOOK_IGNORED_ACTOR_IDS` with Plane user IDs for the
gateway service account, OpenClaw write-back automation, Codex/ChatGPT
integration users, or n8n automation actors. Matching webhook deliveries are
acknowledged, logged with `suppressed_reason=ignored_actor`, and not queued.

Gateway dispatch to OpenClaw is a separate authenticated step. The dispatcher
reads pending normalized events from the queue, posts them to the fixed n8n
`N8N_PLANE_WEBHOOK_DISPATCH_PATH`, and records only successful delivery IDs as
dispatched. Failed downstream sends remain pending and must be retried by a
later dispatch call or scheduler run.

The authenticated queue diagnostics endpoint is read-only. It reports total
valid queued records, dedupe entries, dispatched delivery IDs, still-pending
events, malformed records, and the last safe delivery/correlation identifiers
without returning raw payloads or marking anything dispatched.

The repo-managed n8n dispatch template is:

- workflow: `apps/utilities/n8n/workflows/plane-openclaw-dispatch.workflow.json`
- webhook path: `/webhook/plane-openclaw-dispatch`
- sender: `apps/utilities/n8n/scripts/send-plane-openclaw-dispatch.sh`
- default OpenClaw command: `tools/bin/openclaw-plane-n8n-dispatch`

Import and enable the workflow in live n8n only after Komodo has the SSH mount,
`OPENCLAW_PLANE_DISPATCH_COMMAND`, and real Plane automation actor IDs ready.
The template is deliberately checked in with `active: false`.

The first repo-managed read-only n8n report automation is:

- workflow: `apps/utilities/n8n/workflows/plane-workflow-report.workflow.json`
- script: `apps/utilities/n8n/scripts/plane-workflow-report.js`
- gateway URL env: `MEDIA_GATEWAY_URL`
- gateway token env: `MEDIA_GATEWAY_TOKEN`
- Plane project env: `PLANE_REPORT_PROJECT_ID`

This workflow is deliberately checked in with `active: false`. It calls the
gateway's authenticated Plane read endpoints, emits a compact JSON summary, and
does not write to Plane, Slack, GitHub, or OpenClaw. Import and enable it in
live n8n only after the gateway token and report project ID are configured in
Komodo or n8n runtime settings.

## Metadata Contract

Every automation-visible ticket should expose or derive:

- `identifier` or Plane sequence ID.
- Plane workspace slug.
- Project ID.
- Current state.
- Priority.
- Labels.
- Parent issue or epic, if any.
- Source system and source identifier during migration.
- Repository/path hint when implementation belongs in a repo.
- External UI checklist items when applicable.

Gateway and MCP clients should consume these fields through typed models rather
than embedding raw Plane payload assumptions in each consumer.

## Pre-Import Versus Cutover

Safe before import:

- Create Plane states.
- Create label namespaces and obvious missing labels.
- Document templates.
- Configure projects/workspaces.
- Run small smoke imports into a test project.
- Add gateway read paths and read-only smoke commands.

Requires migration/cutover window:

- Bulk import of Linear issues.
- State remapping for `agent:ready` to `Ready for Agent`.
- Relationship, comment, attachment, and link import.
- Switching OpenClaw/Codex/n8n source of truth from Linear to Plane.
- Enabling Plane webhook automation for real pickup/write-back.
- Disabling old Linear polling/webhook automation.

## Dry-Run Validation Set

Use the OPN-269 migration runbook at
`docs/migrations/2026-07-11-opn-269-linear-to-plane-migration.md` as the
operator checklist for export scope, dry-run import, verification, discrepancy
review, cutover, rollback, and post-cutover validation.

Before broad import, validate this workflow against representative tickets:

- Umbrella epic with child tickets: OPN-264.
- Repo-managed infrastructure install: OPN-267.
- Workflow design/documentation ticket: OPN-268.
- Migration ticket: OPN-269.
- SDK/gateway implementation ticket: OPN-270.
- Webhook automation ticket: OPN-271.
- ChatGPT/Codex integration ticket: OPN-272.
- Agent workflow automation ticket: OPN-273.
- n8n automation ticket: OPN-274.

The dry run must record:

- source Linear status and labels,
- proposed Plane state and labels,
- any ambiguity,
- whether the ticket meets the agent-ready checklist,
- whether a manual correction is required before import.

## Rollback

If this workflow proves too complex before import, use this reduced state set:

- Backlog
- Todo
- Ready for Agent
- In Progress
- Needs Input
- Blocked
- In Review
- Done
- Canceled

Keep `Duplicate` as a label or relation if Plane state limits make a duplicate
state impractical. Do not drop source Linear labels or status evidence during
rollback; preserve it in migration metadata or discrepancy notes.
