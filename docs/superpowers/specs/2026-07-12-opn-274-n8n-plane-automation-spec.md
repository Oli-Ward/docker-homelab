# OPN-274 n8n Plane Automation Spec

## Goal

Define the durable n8n automation boundary for Plane after OPN-270, OPN-271,
OPN-272, and OPN-273 stabilize. OPN-274 should add useful reporting and
notification workflows first, then write-capable workflows only after
idempotency, loop prevention, credentials, rollback, and live smoke evidence
are proven.

Exact webhook field mappings remain owned by OPN-271. Until OPN-271 is stable,
n8n workflows must consume only the gateway's normalized allowlisted fields or
authenticated gateway read endpoints, not raw Plane webhook payloads.

## Non-Goals

- Do not make n8n part of the core agent pickup path required by OPN-273.
- Do not couple n8n workflows directly to raw Plane webhook payload shape.
- Do not store Plane, Slack, GitHub, gateway, or n8n credentials in this repo.
- Do not enable write-back workflows before a read-only workflow has run
  successfully against the live Plane workspace.
- Do not use n8n workflow activation as a substitute for Komodo-controlled
  deployment of repo-managed files and environment.
- Do not mutate live Plane, Slack, GitHub, Docker, or Komodo state from this
  spec alone.

## Current Baseline

OPN-274 already has one repo-managed read-only workflow slice:

- workflow: `apps/utilities/n8n/workflows/plane-workflow-report.workflow.json`
- script: `apps/utilities/n8n/scripts/plane-workflow-report.js`
- tests:
  - `apps/utilities/n8n/scripts/test-plane-workflow-report.js`
  - `apps/utilities/n8n/scripts/test-plane-workflow-report-workflow.js`
- status: checked in with `active: false`
- behavior: scheduled report script calls authenticated gateway Plane read
  endpoints, emits compact JSON, and writes to no external system

This baseline is the first workflow. OPN-274 is not complete until it is
imported/enabled in live n8n with real runtime credentials, run successfully
against the live Plane workspace, and documented with external enablement
evidence.

## Automation Classes

OPN-274 automations are grouped by increasing risk.

| Class | Writes external state? | Initial status | Examples |
| --- | --- | --- | --- |
| `read-report` | No | Allowed first | Workflow summary, blocked tickets, stale review list |
| `notify` | Slack only | Allowed after read-report smoke | Daily/weekly Slack digest, Needs Input alert |
| `reconcile` | Plane comments or labels | Later | PR merged comment, stale In Review comment |
| `transition` | Plane state changes | Last | Move PR-merged ticket to In Review or Done candidate |

Each workflow must declare its class in docs and tests. Higher-risk classes
inherit all lower-risk requirements.

## First Workflows

### 1. Plane Workflow Report

Purpose: provide a scheduled read-only summary of Plane work item state so the
live gateway, n8n runtime, and Plane read credentials are proven before any
write path exists.

Trigger:

- n8n schedule trigger, initially weekly.
- Manual n8n execution is allowed for smoke testing.

Reads:

- Gateway `/v1/workflow/plane/projects/{project_id}/states`.
- Gateway `/v1/workflow/plane/projects/{project_id}/work-items`.

Writes:

- n8n execution output only.
- No Plane, Slack, GitHub, OpenClaw, Docker, or Komodo writes.

Expected output:

- JSON report with `source`, `report`, `generated_at`, `project_id`,
  `total_items`, `counts_by_state`, `counts_by_priority`,
  `ready_for_agent_count`, `blocked_count`, and compact `items`.
- No raw Plane payloads, descriptions, comments, tokens, or credentials.

Rollback switch:

- Disable `plane-workflow-report` in n8n.
- If runtime env is wrong, remove or blank only the n8n runtime variables;
  repo files can remain checked in.

### 2. Slack Plane Digest

Purpose: post a concise scheduled summary only after the read-only report is
stable and considered useful.

Trigger:

- n8n schedule trigger, daily or weekly.
- Optional manual execution for smoke testing.

Reads:

- Reuse the Plane workflow report script output, or call the same gateway read
  endpoints through a small checked-in script.

Writes:

- One Slack message to an approved channel.
- No Plane writes.

Noise controls:

- Include only counts, top blocked items, Needs Input items, stale In Review
  items, and a link or identifier per item.
- Do not post if the report has no actionable items unless explicitly
  configured.
- Keep a single configured channel; do not DM multiple users from the first
  version.

Rollback switch:

- Disable the Slack digest workflow in n8n.
- Revoke or rotate the Slack credential outside Git if needed.

### 3. Blocked And Needs Input Escalation

Purpose: surface tickets that need human attention without modifying Plane
state.

Trigger:

- n8n schedule trigger, daily.

Reads:

- Gateway or Plane SDK-backed helper read for tickets in `Blocked` or
  `Needs Input`.
- Ticket age or `updated_at` when available through stable gateway fields.

Writes:

- Slack notification only.
- No Plane comments or transitions in the first version.

Escalation policy:

- `Needs Input` older than 24 hours can be included.
- `Blocked` older than 48 hours can be included.
- Terminal states are ignored.
- Suppressed labels such as `manual`, `no-agent`, or `agent:hold` are reported
  only if the report is explicitly configured to include them.

Rollback switch:

- Disable the workflow in n8n.

### 4. PR Merge Reconciliation

Purpose: reconcile GitHub PR merge events back to Plane only after write
idempotency and loop prevention are proven.

Trigger:

- GitHub merged PR event or scheduled poll of merged PRs.

Reads:

- GitHub PR metadata.
- Ticket identifier parsed from branch name, commit subject, or PR title.
- Plane ticket through gateway/Plane SDK helper.

Writes:

- First write version may add a Plane comment only.
- State transition to `In Review` or `Done` requires a separate approval rule
  and fresh verification evidence.

Rollback switch:

- Disable the workflow in n8n.
- Keep GitHub and Plane state unchanged; duplicate comments must be prevented
  by idempotency keys.

## Trigger Boundaries

n8n may consume these trigger sources:

- Schedule triggers for reports, summaries, and stale-ticket checks.
- Gateway-dispatched normalized Plane webhook events from OPN-271.
- GitHub webhook or polling events for PR reconciliation.
- Slack slash command or interaction triggers only after the Slack digest is
  stable.

n8n must not consume:

- Raw Plane webhook payloads directly from Plane.
- Redis queue internals owned by OPN-271.
- OpenClaw agent claim store internals owned by OPN-273.
- Live Docker or Komodo mutation triggers.

## Read/Write Boundaries

### Reads Allowed

- Authenticated gateway Plane read endpoints.
- A helper service or CLI using `packages/openclaw-plane-sdk` after OPN-270 is
  stable.
- GitHub PR read APIs for reconciliation workflows.
- Slack channel/user metadata only when needed for an approved notification.

### Writes Allowed

- n8n execution output and logs, excluding secrets and raw payloads.
- Slack messages for approved notification workflows.
- Plane comments only after a workflow has a documented idempotency key and
  duplicate suppression test.
- Plane state transitions only after a separate approval rule and rollback
  note exist.

### Writes Forbidden

- Secrets, tokens, raw webhook payloads, request headers, cookies, private keys,
  runtime histories, sqlite state, or `.env` files.
- Plane comments containing raw payload dumps or credential-bearing URLs.
- Direct Docker, Komodo, Nginx Proxy Manager, Authentik, AdGuard, or filesystem
  mutations.
- Agent pickup claims, branches, commits, PRs, or Codex sessions. Those remain
  OPN-273 concerns.

## Credential Model

Credentials are runtime-only and stored outside Git.

Required for the current read-only report:

- `MEDIA_GATEWAY_URL`
- `MEDIA_GATEWAY_TOKEN`
- `PLANE_REPORT_PROJECT_ID`
- optional `PLANE_REPORT_LIMIT`

Future workflow credentials:

- Slack bot credential or webhook URL, stored in n8n credentials or Komodo
  runtime config.
- GitHub app/token credential, scoped read-only until a write workflow needs
  more.
- Plane API credential only if direct Plane SDK helper access is approved;
  gateway access is preferred for initial workflows.

Credential rules:

- Example env files may contain safe placeholders only.
- Tests must use fake tokens.
- Scripts must fail closed with `Set <ENV_NAME>` style errors when required
  env vars are missing.
- Scripts must not echo bearer tokens, webhook URLs, API keys, or raw headers.
- Workflow exports must not contain real credentials, credential IDs that imply
  secret values, or captured production output.

## Version-Controlled Exports

Every repo-managed n8n workflow must have:

- A disabled workflow export under `apps/utilities/n8n/workflows/*.workflow.json`.
- Checked-in helper script under `apps/utilities/n8n/scripts/` when command or
  transformation logic is non-trivial.
- A focused script test and a workflow structure test.
- Runtime env placeholders in `apps/utilities/example.env` when new env vars
  are required.
- Compose env passthrough in `apps/utilities/compose.yml` when n8n needs the
  variable at runtime.
- Documentation in `docs/workflow/plane.md` or a workflow-specific doc.

Workflow exports must keep `active: false`. Live activation happens in n8n
after Komodo deploys the repo changes and runtime credentials are configured.

## Idempotency Requirements

All workflows:

- Use a stable `correlation_id` when one is provided by OPN-271 or gateway read
  output.
- Include workflow name and source identifier in logs and output.
- Treat missing stable identifiers as `needs_input` or no-op for write-capable
  flows.

Slack notification workflows:

- May use a coarse scheduled window key such as
  `n8n:{workflow}:{project_id}:{yyyy-mm-dd}`.
- Should avoid repeated posts for the same actionable set within the same
  schedule window.

Plane comment workflows:

- Use idempotency key
  `n8n:{workflow}:{plane_project_id}:{plane_work_item_id}:{phase}:{source_revision}`.
- Check for an existing marker before writing.
- Include a safe hidden or visible marker in the comment, such as
  `n8n-idempotency: <key>`, only if that does not create user-facing noise.
- Retrying the same event must not create a second comment.

Plane state transition workflows:

- Use idempotency key
  `n8n:{workflow}:{plane_project_id}:{plane_work_item_id}:transition:{from_state}:{to_state}:{source_revision}`.
- Re-read the ticket immediately before transition.
- No-op if the current state no longer matches the expected source state.
- Never transition terminal tickets.
- Never transition to `Done` without fresh verification evidence and explicit
  workflow-specific approval rules.

## Loop Prevention

n8n must ignore or suppress events caused by:

- the n8n automation actor,
- the gateway service account,
- OpenClaw write-back automation,
- Codex/ChatGPT integration users,
- the same workflow's prior write-back marker or correlation ID.

Loop prevention may use:

- OPN-271 `actor_id` and ignored actor list when present,
- stable `correlation_id`,
- workflow-specific idempotency marker,
- source revision or delivery ID,
- state re-read before write.

If actor identity is missing on a write-capable trigger, the workflow must not
write to Plane.

## Failure Handling

Retryable failures:

- gateway, Plane, GitHub, Slack, or n8n 429/5xx responses,
- temporary DNS/network failures,
- n8n execution timeout,
- credential store temporarily unavailable.

Permanent failures:

- missing required env vars,
- missing stable ticket identifier for a write workflow,
- unauthorized or forbidden response until credentials are fixed,
- unsupported event type,
- missing actor identity for a write workflow,
- malformed normalized event after OPN-271 stabilizes.

Failure output:

- Read-only workflows fail the execution and log a concise non-secret error.
- Slack workflows fail closed; they do not post partial or fallback messages
  containing raw diagnostic payloads.
- Plane write workflows record a safe n8n failure state and do not transition
  Plane after partial failure unless the idempotency check confirms the write
  already happened.

## Test Plans

Each workflow must include local tests before live import.

Read-only report tests:

- script test with fake gateway responses,
- workflow JSON structure test,
- env missing tests where helper script complexity justifies them,
- no raw payload forwarding assertion,
- `docker compose -f apps/utilities/compose.yml --env-file apps/utilities/example.env config --quiet`,
- `git diff --check`.

Slack notification tests:

- fake report input to message formatting,
- no-post behavior when no actionable items exist,
- channel/output destination is configurable,
- no token or webhook URL appears in output,
- workflow export remains `active: false`.

Plane write tests:

- duplicate event does not duplicate comment,
- stale state re-read prevents transition,
- automation actor event is ignored,
- terminal states are ignored,
- missing actor identity fails closed,
- idempotency marker or audit key is present,
- retry after transient failure reuses the same key.

Live smoke checklist:

- Import disabled workflow into n8n.
- Configure real credentials outside Git through Komodo or n8n runtime
  credential storage.
- Manually execute read-only workflow and capture non-secret output summary.
- Enable schedule only after manual execution succeeds.
- For notification workflows, send to an approved low-noise channel first.
- For write workflows, use a test project or marked test ticket first.
- Record the workflow name, trigger, credentials location category, expected
  output, rollback switch, and smoke result in `docs/workflow/plane.md` or the
  ticket update.

## Rollback Switches

Every workflow must have a simple rollback switch:

- Primary: disable the workflow in n8n.
- Secondary: remove or blank runtime env vars/credentials outside Git.
- Tertiary: revert the repo-managed workflow export/script change and redeploy
  through Komodo.

Rollback must not require changing Plane ticket data manually. If a workflow
can write Plane comments or state transitions, its spec must describe how to
identify its prior writes through idempotency markers or audit keys.

## Done Criteria

OPN-274 is Done when:

- At least one n8n Plane automation has run successfully against the live Plane
  workspace.
- Credentials used by that workflow are stored outside the repo and were not
  printed, committed, or captured in workflow exports.
- The workflow docs include trigger, dependencies, credentials category,
  rollback switch, and expected output.
- The read-only report or Slack/reporting output is useful and not noisy.
- Any write-capable workflow included in the ticket has proven idempotency and
  loop-prevention tests.
- The live workflow can be disabled without breaking Plane, OpenClaw, gateway,
  or OPN-273 agent pickup.

## Open Decisions

- Whether the first live output should remain n8n execution JSON only or post a
  Slack digest after the read-only report smoke.
- Whether future workflows should call Plane only through gateway endpoints or
  through a small helper built on `packages/openclaw-plane-sdk`.
- Which Slack channel, if any, is approved for Plane automation summaries.
- Which Plane automation actor IDs must be configured in OPN-271 ignored actor
  lists before write workflows are enabled.
- Exact normalized webhook field names for webhook-triggered workflows; leave
  these to OPN-271 and consume only stable adapter output once available.
