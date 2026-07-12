# Plane Cutover Readiness

Date: 2026-07-12

## Verified Live

- Komodo CLI is configured locally at `~/.config/komodo/komodo.cli.toml` with mode `0600`.
- `km core-info` succeeds against local Komodo Core on `http://127.0.0.1:9120`.
- Komodo Core runtime `webhook_base_url` now reports `https://komodo.home.lab`.
- `km list stacks --all` shows the `plane` stack managed in Komodo.
- Komodo reports the `plane` stack as `running` after moving the successful
  one-shot `migrator` service behind the explicit `migration` profile and
  redeploying through Komodo. The old `plane-migrator-1` exited container still
  exists in Docker history, but it no longer affects Komodo stack health.
- `plane.home.lab` routes through Nginx Proxy Manager to the Plane proxy on `192.168.1.103:8085`.
- Browser-facing route returns `HTTP/2 200` with Plane HTML through `openresty` and Caddy.
- Desktop and iPhone Plane login were human-confirmed by the user.
- Direct Plane proxy root on `127.0.0.1:8085` still returns `HTTP 200` with an empty body, so use the NPM host route for browser/API validation.
- TLS certificate presented for `plane.home.lab` is the homelab/mkcert certificate with `*.home.lab` SAN coverage.
- Plane backend env is aligned to `https://plane.home.lab`, including `WEB_URL`, `PI_BASE_URL`, and `CORS_ALLOWED_ORIGINS`.
- Plane backend containers trust the homelab CA; `plane-api-1` can fetch `https://auth.home.lab/` and `https://plane.home.lab/` without certificate failures.
- Plane stateful mounts are under `/srv/appdata/plane`, including PostgreSQL, Redis, RabbitMQ, MinIO, monitor state, logs, and Caddy state.
- `plane-web-1`, `plane-admin-1`, and `plane-space-1` reported healthy.
- Gateway-to-Plane API path is fixed and live:
  - `openclaw-gateway` resolves `plane.home.lab` to `192.168.1.103`.
  - `openclaw-gateway` can call `https://plane.home.lab/api/v1/...` with CA verification enabled.
  - Gateway project list returns the `Openclaw` Plane project.
  - Gateway label route now returns live labels after changing the SDK labels path from `/work-item-labels/` to `/labels/`.
- Gateway write smoke created Plane work item `67cf0631-2ab8-44ab-ba63-2745259b100e` / sequence `206` and a comment.
- Plane backup checkpoint created:
  - path: `/mnt/backup/plane/plane-2026-07-12T01-51-35Z`
  - `plane-db.dump`: logical PostgreSQL custom-format dump
  - `plane-db-globals.sql`: PostgreSQL globals dump
  - `plane-appstate-excluding-db.tar.gz`: Plane app-state archive excluding raw
    PostgreSQL files
  - `manifest.txt`: repo/status/container/count metadata
  - `SHA256SUMS`: hash manifest
- Backup verification:
  - `sha256sum -c SHA256SUMS` passed for all artifacts.
  - `pg_restore -l plane-db.dump` listed Plane tables including `issues`,
    `issue_comments`, and `projects`.
  - A temporary archive readback extracted Caddy, MinIO, and log paths outside
    live appdata.
- Backup limitation: this checkpoint is local and root-owned but not encrypted
  because no `BACKUP_AGE_RECIPIENT` or recipient file was configured in this
  session.

## Runtime Config Applied Outside Git

- `apps/openclaw-gateway/.env` now has a real `PLANE_WEBHOOK_SECRET`.
- `apps/openclaw-gateway/.env` now has `PLANE_WEBHOOK_IGNORED_ACTOR_IDS` set to the Plane actor ID used by the gateway API key.
- `apps/utilities/.env` now has `MEDIA_GATEWAY_URL`, `MEDIA_GATEWAY_TOKEN`, `PLANE_REPORT_PROJECT_ID`, and `OPENCLAW_PLANE_DISPATCH_COMMAND`.
- `openclaw-gateway` was recreated so the webhook secret and ignored actor list are live.
- `n8n` was recreated so the Plane workflow env is live.

## n8n

- Imported workflows:
  - `plane-openclaw-dispatch`
  - `plane-workflow-report`
- Enabled workflows with `n8n update:workflow --active=true` and restarted `n8n`.
- `plane-workflow-report.js` ran inside `n8n` and successfully read Plane through the gateway:
  - `total_items`: 100 at the configured report limit.
  - `ready_for_agent_count`: 0.
  - `blocked_count`: 2.
- Required n8n env is now present in the live container:
  - `MEDIA_GATEWAY_URL`
  - `MEDIA_GATEWAY_TOKEN`
  - `PLANE_REPORT_PROJECT_ID`
  - `OPENCLAW_PLANE_DISPATCH_COMMAND`
  - OpenClaw SSH host/user/key/workspace values.

## Plane Webhook

- Plane webhook registration was created in Plane:
  - URL: `http://192.168.1.103:8088/v1/workflow/plane/webhook`
  - Active: yes
  - Scopes: issue and issue comment
  - Webhook ID: `783af562-44d3-4d15-899a-0c36a267c55d`
- Plane worker and API containers can reach `http://192.168.1.103:8088/health`.
- Gateway queue status after config:
  - `configured`: true
  - `pending_count`: 0 after dispatch
  - `malformed_count`: 0
- Synthetic signed gateway ingress smoke:
  - Gateway accepted the signed Plane-format delivery.
  - Gateway queued it.
  - Gateway dispatched it to n8n.
  - Queue returned to zero pending.
- Real Plane sender-task smoke:
  - Plane's own webhook sender used the stored Plane webhook record and secret.
  - Plane logged webhook response status `200`.
  - Gateway queued the Plane-sent delivery.
  - Gateway dispatched it to n8n.
  - Queue returned to zero pending.

## Migration Dry-Run Status

Dry-run import into the current Plane project was initially not run by this
session. A later user-run Plane beta Linear import created a partial import.

Initial Plane beta import report evidence:

- Finished import job: `3b2cc018-c6b9-4be2-8c7b-f728c9500a66`
- Source: `LINEAR`
- Status: `FINISHED`
- Plane report: `250` total issues, `198` imported issues, `52` errored issues.
- `import_execution_logs` contained no rows for the failed items, so Plane did not preserve a useful per-issue error list.
- Current Plane project count: `206` live issues:
  - `198` imported Linear issues with `external_source = LINEAR`
  - `7` Plane onboarding issues
  - `1` gateway write-smoke issue

Local Linear-vs-Plane diff evidence:

- Current active/non-archived Linear Openclaw team count: `249`
- Plane imported Linear issue count: `198`
- Missing active/non-archived Linear issues in Plane: `51`
- Missing by Linear project:
  - `OpenClaw Build Plan`: `39`
  - `Session`: `12`
- Missing by Linear state:
  - `Done`: `30`
  - `In Progress`: `8`
  - `In Review`: `6`
  - `Backlog`: `4`
  - `Blocked`: `3`
- Missing issue list:
  - `diagnostics/build-lanes/2026-07-12-linear-plane-missing-active-team-issues.tsv`

The one-count difference between Plane's `250` reported total and the current
Linear active-team count of `249` is likely timing-related; `OPN-275` was
created after the import window.

Original reasons for avoiding a blind rerun still apply:

- No verified Plane backup/restore checkpoint ID is available yet.
- `apps/plane/README.md` explicitly requires a dedicated Plane backup/restore lane before imports or state moves.
- The current Plane project already contains imported/migrated work items and onboarding items, so another dry-run import into it would risk duplicates and make discrepancy analysis noisy.
- Linear `OpenClaw Build Plan` readback showed no next page at a 250 item page size, but the existing Plane project already has enough imported items that a clean count comparison needs an isolated target project or a restoreable snapshot.

Required recovery shape:

1. Capture and record a restoreable Plane snapshot/archive ID.
2. Do not rerun the Plane beta importer over the same target without duplicate
   controls.
3. Use `issues.external_id` / `external_source = LINEAR` as the idempotency key.
4. Run a supplemental import for the missing Linear UUIDs only.
4. Compare:
   - issue count
   - state/status mapping
   - priorities
   - labels
   - parent/child links
   - related/dependency links
   - comments
   - attachments and external links
5. Document discrepancies before final import.

Supplemental recovery completed:

- Root cause from Plane worker logs: failed imported rows were rejected with
  `invalid_parent_id`; the importer passed Linear parent identifiers into
  Plane's `parent` field before they were resolvable as Plane issue UUIDs.
- All `51` missing active/non-archived Linear issues had Linear parents.
- Supplemental import used `external_source = LINEAR` and Linear UUIDs as the
  idempotency key.
- Supplemental import created or found all `51` missing issues:
  - `39` created in the final retrying run.
  - `12` already existed from the earlier rate-limited partial run.
- Supplemental import added all `51` Linear issue links.
- Supplemental import added all `161` exported Linear comments.
- Supplemental parent repair set all `51` parent relationships after the Plane
  issue UUIDs were known.
- Post-recovery Plane count: `249` Linear-sourced issues, matching the current
  active/non-archived Linear Openclaw team count of `249`.
- Post-recovery checks:
  - missing supplemental issue IDs: `0`
  - supplemental issues without parents: `0`
  - supplemental imported comments: `161`
  - supplemental Linear links: `51`
- Known remaining import discrepancy: Linear label `tag:docs` was present on
  one supplemental issue but did not exist in Plane, so it was not invented
  during recovery. Existing Plane label `area:hygiene` was preserved where
  present.

## Remaining Blockers

- Komodo's stack health view treats the successful one-shot Plane migrator container as an exited service, making the Plane stack look unhealthy despite the application containers running. Decide whether to adjust the stack definition/status expectations after confirming Plane's recommended migrator lifecycle.
- OpenClaw-side Plane pickup is not complete. The live n8n/OpenClaw SSH path is
  configured and reachable, but the configured
  `tools/bin/openclaw-plane-n8n-dispatch` command is missing in the OpenClaw
  workspace. Existing OpenClaw helper work covers Linear-era/Plane-compatible
  preview and queueing, but not the real Plane dispatch command, durable claim
  store, repo routing, Codex handoff, branch/PR linking, retries, or Plane
  write-back.
- ChatGPT/Codex Plane tools are not implemented. The gateway has authenticated Plane routes and audit behavior, but there is no proven MCP/ChatGPT/Codex tool surface for create/search/read/update/comment.
- Linear should remain the source of truth until the isolated import verification and OpenClaw-side pickup/write-back are complete.

## Cutover Plan

Do not approve final cutover yet.

Cutover prerequisites:

1. Human-confirm desktop and iPhone Plane login.
2. Replace or supplement the local unencrypted Plane checkpoint with the final
   encrypted/off-host backup policy if needed.
3. Run isolated Linear-to-Plane dry-run and record discrepancy table.
4. Finish OpenClaw-side pickup and write-back.
5. Prove ChatGPT/Codex Plane tool integration live.
6. Freeze Linear writes.
7. Run final import.
8. Verify final counts and relationships.
9. Disable old Linear pickup/write-back paths.
10. Keep rollback ready using the recorded Plane checkpoint and Linear freeze point.
