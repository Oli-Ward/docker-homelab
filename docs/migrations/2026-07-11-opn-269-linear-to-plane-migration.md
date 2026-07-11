# OPN-269 Linear to Plane Migration Runbook

This runbook is the durable operator checklist for migrating the OpenClaw
planning backlog from Linear to Plane. It turns the OPN-269 ticket into
explicit gates so the dry run, discrepancy review, cutover, and rollback can
be verified before Linear stops being the source of truth.

Do not run a production import until this runbook has been filled with current
evidence and explicitly approved for the cutover window.

## Scope Freeze

Record the migration scope before any export or import.

| Decision | Value | Evidence |
| --- | --- | --- |
| Linear team(s) included | Openclaw | Linear issue/project query used for export |
| Linear project(s) included | OpenClaw Build Plan | Linear project query used for export |
| Parent epic included | OPN-264 | Parent/child issue list export |
| Child tickets included | OPN-267 through OPN-274 at minimum | Parent issue children export |
| Completed issues | Include unless explicitly excluded | Export count by status |
| Canceled issues | Include as Canceled unless explicitly excluded | Export count by status |
| Archived issues | Decide before export | Export flag and count |
| Attachments | Migrate as Plane attachments or preserve as external links/deferred list | Attachment inventory |
| Comments | Preserve chronological comments where Plane import supports them | Comment count comparison |
| Source of truth during dry run | Linear | Dry run must not disable Linear automations |

If the scope changes after dry-run export, restart the dry run from export
rather than patching the report by hand.

## Preconditions

- Plane stack is deployed through Komodo from `apps/plane`.
- Plane is reachable from desktop and iPhone.
- Plane backup or VM snapshot exists and has an operator-visible restore path.
- Plane workflow states and labels from `docs/workflow/plane.md` exist in the
  dry-run target.
- Gateway read paths and the `openclaw_plane_sdk` client have passed local
  tests.
- Real Plane and Linear credentials are stored outside Git.
- Old Linear polling/webhook automations remain enabled until cutover approval.
- Plane webhook write-back automation remains disabled during the dry run unless
  the event target is an isolated test project.

## Backup And Safety Gate

Before the first dry import:

1. Confirm a current VM snapshot or Plane appdata/database backup exists.
2. Record the backup identifier, timestamp, and restore owner in the migration
   report.
3. Confirm the dry-run import target is not the production Plane project that
   humans will use after cutover.
4. Confirm the rollback owner has permission to disable Plane automations and
   return Linear to source-of-truth status.

Do not delete failed dry-run imports unless cleanup has separate explicit
approval.

## Read-Only Linear Export

The export phase must be read-only against Linear.

Capture these artifacts outside Git if they contain private issue data:

| Artifact | Required evidence |
| --- | --- |
| Issues | Total count, count by status, priority, project, parent, and assignee |
| Labels | Full label list and count of label uses |
| Comments | Comment count per representative ticket and total comment count if available |
| Links | Link count and representative URL preservation check |
| Attachments | Attachment count and chosen migration policy |
| Relationships | Parent/child count and related/blocking relationship count |
| Export timestamp | UTC timestamp and actor/tool that ran export |

The repo may store summary reports and discrepancy templates, but not raw
private exports, tokens, cookies, or attachment payloads.

## Field Mapping Gate

Use `docs/workflow/plane.md` as the mapping source of truth.

| Linear field | Plane target | Gate |
| --- | --- | --- |
| Issue identifier | Preserve in title, description metadata, or custom field if available | Every migrated issue can be traced back to Linear |
| Title/body | Plane work item title/description | Representative body formatting spot checks pass |
| Status | Plane state | Counts by mapped status reconcile or discrepancies are listed |
| `agent:ready` label | Ready for Agent state only when safe | Hold/risk labels suppress promotion |
| Priority | Plane priority | Counts by priority reconcile |
| Labels | Namespaced Plane labels | Unknown labels are mapped or listed for creation |
| Parent issue | Plane parent/child relation | OPN-264 child set is preserved |
| Related/blocking links | Plane relation or description backlink | Unsupported relations are documented |
| Comments | Plane comments | Representative chronology and author/timestamp policy are documented |
| Attachments | Plane attachments or external links | Every omitted attachment appears in discrepancy report |

## Dry-Run Import

Run the first import into a dedicated test Plane project or workspace area.

Dry-run target record:

```text
Plane workspace:
Plane test project:
Import tool/version:
Import started:
Import completed:
Operator:
Source export timestamp:
```

During dry run:

1. Keep Linear as source of truth.
2. Keep production Plane pickup/write-back automations disabled.
3. Import a representative slice first: OPN-264 and OPN-267 through OPN-274.
4. Import broader issue scope only after the representative slice verifies.
5. Stop on schema, auth, rate-limit, or relationship errors and record the
   failed object identifier before retrying.

## Verification Matrix

Fill this table after each dry run and final import.

| Check | Source count | Plane count | Result | Evidence |
| --- | ---: | ---: | --- | --- |
| Included issues |  |  |  | Export/import report |
| Backlog |  |  |  | Status count report |
| Todo |  |  |  | Status count report |
| Ready for Agent |  |  |  | Label/state mapping report |
| In Progress |  |  |  | Status count report |
| Needs Input |  |  |  | Status count report |
| Blocked |  |  |  | Status count report |
| In Review |  |  |  | Status count report |
| Done |  |  |  | Status count report |
| Canceled |  |  |  | Status count report |
| Duplicate |  |  |  | Status count report |
| Labels |  |  |  | Label use count report |
| Priorities |  |  |  | Priority count report |
| Parent/child relations |  |  |  | Relationship report |
| Related/blocking relations |  |  |  | Relationship report |
| Comments |  |  |  | Comment count report |
| Links |  |  |  | Link count report |
| Attachments or deferred attachments |  |  |  | Attachment policy report |

Counts do not need to match when Plane lacks a corresponding feature, but every
mismatch needs a named discrepancy and an explicit acceptance or fix decision.

## Representative Spot Checks

Spot-check these tickets in every dry run:

- OPN-264: umbrella epic with child links and cutover checklist.
- OPN-267: install/configuration ticket with external UI and backup work.
- OPN-268: workflow design documentation ticket.
- OPN-269: this migration ticket.
- OPN-270: SDK/gateway implementation ticket.
- OPN-271: webhook automation ticket.
- OPN-272: ChatGPT/Codex integration ticket.
- OPN-273: agent automation ticket.
- OPN-274: n8n automation ticket.

For each ticket, verify:

- title,
- body sections,
- status/state,
- priority,
- labels,
- parent/child relationship,
- comments,
- links,
- attachment policy,
- source Linear identifier traceability.

## Discrepancy Report Format

Record every discrepancy in this shape:

```text
Discrepancy ID:
Source Linear object:
Plane object:
Category: status | label | priority | body | comment | link | attachment | relation | missing | duplicate | other
Observed:
Expected:
Impact:
Decision: fix before cutover | accept with note | defer follow-up | exclude from scope
Owner:
Resolved evidence:
```

The cutover cannot proceed while any discrepancy is marked `fix before cutover`
without resolved evidence.

## Cutover Checklist

Complete this only after an acceptable dry run.

1. Announce Linear freeze window.
2. Disable or pause old Linear pickup/write-back automations at the approved
   time.
3. Run final read-only Linear export.
4. Record final export timestamp.
5. Run final Plane import into production target.
6. Run the verification matrix against final import.
7. Spot-check representative tickets.
8. Enable only the Plane automations approved for cutover.
9. Run a non-critical Plane ticket smoke for gateway read/write paths.
10. Run a non-critical Plane agent pickup dry run before real pickup.
11. Update OPN-264 with final migration report and source-of-truth decision.
12. Get explicit approval before declaring Linear no longer source of truth.

## Rollback Checklist

Use this if final import or initial Plane operation fails.

1. Disable Plane pickup/write-back/n8n automations.
2. Keep Linear as or restore Linear to source of truth.
3. Re-enable old Linear polling/webhook automation only if it was disabled and
   is still known-good.
4. Preserve the failed Plane import for inspection unless cleanup is explicitly
   approved.
5. Record failure evidence, failed object identifiers, and operator actions.
6. Create follow-up tickets for fixes before the next import attempt.

Rollback must not delete Linear data. Rollback must not remove Plane data or
attachments without explicit destructive-cleanup approval.

## Post-Cutover Validation

Within the first operating window after cutover, verify:

- new Plane tickets can be created through the approved integration path,
- gateway read paths return expected Plane project/state/label/work-item data,
- a test progress comment can be written to a marked smoke ticket,
- webhook ingress receives a test event and records a correlation ID,
- n8n/OpenClaw dispatch handles a test event without duplicate work,
- old Linear automation is disabled or explicitly marked read-only,
- OPN-264 contains the final migration report and known discrepancies.

## Remaining Manual Work

This runbook does not perform the export/import. It defines the required gates
and evidence for OPN-269. The actual dry run, final import, live smoke, and
source-of-truth switch remain manual or tool-assisted operator actions.
