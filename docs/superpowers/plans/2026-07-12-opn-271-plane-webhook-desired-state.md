# OPN-271 Plane Webhook Desired State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring OPN-271 to the 2026-07-12 Linear desired state: Plane webhook events are validated, normalized into a full internal envelope, allowlist-filtered, deduplicated, durably queued in Redis, dispatched to OpenClaw through n8n, retried with backoff, dead-lettered when exhausted or permanent, replayable, observable, and live-smoked.

**Architecture:** Preserve the current signed Plane webhook ingress and n8n dispatch path, but replace the production file-backed queue with a Redis-backed queue. Keep raw Plane payloads inside the ingress/normalization boundary only; persist and dispatch normalized envelopes plus raw payload hashes, correlation IDs, and retry metadata. Continue using n8n plus `OPENCLAW_PLANE_DISPATCH_COMMAND` as the resolved OpenClaw dispatch contract, not a new direct OpenClaw HTTP endpoint.

**Tech Stack:** FastAPI, Pydantic, pydantic-settings, httpx, Redis, pytest, respx, Docker Compose, n8n workflow assets, Bash smoke scripts.

## Global Constraints

- Do not run `docker compose up`, `docker compose down`, `docker compose pull`, or restart containers directly unless explicitly asked.
- Komodo is the source of truth for deploying, restarting, updating, and stopping stacks.
- Do not read, print, infer, or commit real `.env` values, webhook secrets, API keys, tokens, private keys, runtime state, queue contents, session history, or credentials.
- Raw Plane payloads must not be persisted or forwarded beyond ingress/normalization; store only a hash and normalized fields.
- Production queueing must use Redis; the existing file-backed queue may remain only as a local-development/test fallback if explicitly named as such.
- Unsupported Plane events must be acknowledged and logged as ignored, not queued or treated as failures.
- Dispatch contract remains gateway -> n8n -> `OPENCLAW_PLANE_DISPATCH_COMMAND` over SSH.
- No direct OpenClaw `/internal/events/plane` endpoint should be added for this ticket.
- Any storage-affecting Redis/Appdata deployment change must call out backup/checkpoint and rollback expectations before live deployment.

---

## Current Baseline To Preserve

Existing committed behavior already includes:

- `POST /v1/workflow/plane/webhook` validates `X-Plane-Signature` HMAC-SHA256 over the raw body using `PLANE_WEBHOOK_SECRET`.
- `X-Plane-Delivery` is required today and is used as the current dedupe/correlation handle.
- Minimal normalized fields are persisted to `FilePlaneWebhookQueue` JSONL and `.seen`/`.dispatched` sidecars.
- `PLANE_WEBHOOK_IGNORED_ACTOR_IDS` suppresses known automation actors before queueing.
- `POST /v1/workflow/plane/webhook/dispatch` forwards pending normalized events to n8n via `N8nClient.forward_plane_webhook_event()`.
- `GET /v1/workflow/plane/webhook/queue` exposes read-only diagnostics for the file queue.
- n8n workflow assets exist for `plane-openclaw-dispatch` and invoke `OPENCLAW_PLANE_DISPATCH_COMMAND --event-file <remote-payload>`.

The old six OPN-271 plans are historical implementation slices. Do not continue implementing from them directly; use this plan as the current source for remaining work.

---

### Task 1: Redis Queue Interface And Local Fallback Boundary

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/pyproject.toml`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/settings.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/plane_webhooks.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_settings.py`
- Create: `apps/openclaw-gateway/openclaw-gateway/tests/test_plane_webhooks_redis.py`
- Modify: `apps/openclaw-gateway/compose.yml`
- Modify: `apps/openclaw-gateway/example.env`

**Interfaces:**
- Produces: `PlaneWebhookQueue` protocol with `enqueue(event)`, `pending_events(limit)`, `mark_dispatched(delivery_id)`, `mark_failed(delivery_id, failure)`, `status()`, and `replay_dead_letter(delivery_id)`.
- Produces: `RedisPlaneWebhookQueue` production implementation.
- Produces: explicit settings for Redis queue mode and Redis URL without putting secrets in docs.

- [ ] **Step 1: Add failing settings tests for Redis queue config**

Add tests in `tests/test_settings.py` proving these defaults and env overrides:

```python
def test_plane_webhook_queue_defaults_to_redis() -> None:
    settings = Settings(gateway_token="gateway-secret", plane_webhook_secret="plane-secret")
    assert settings.plane_webhook_queue_backend == "redis"
    assert settings.plane_webhook_redis_url == "redis://redis:6379/0"
    assert settings.plane_webhook_redis_prefix == "openclaw:plane:webhooks"


def test_plane_webhook_queue_backend_accepts_file_for_local_development() -> None:
    settings = Settings(
        gateway_token="gateway-secret",
        plane_webhook_secret="plane-secret",
        plane_webhook_queue_backend="file",
    )
    assert settings.plane_webhook_queue_backend == "file"
```

- [ ] **Step 2: Add Redis dependency and settings**

Add the async Redis client dependency to `pyproject.toml` if absent:

```toml
redis = ">=5.0,<6.0"
```

Add settings fields:

```python
plane_webhook_queue_backend: Literal["redis", "file"] = "redis"
plane_webhook_redis_url: str = "redis://redis:6379/0"
plane_webhook_redis_prefix: str = "openclaw:plane:webhooks"
```

- [ ] **Step 3: Define a queue protocol before changing callers**

In `openclaw_gateway/plane_webhooks.py`, introduce a small protocol/dataclass boundary:

```python
@dataclass(frozen=True)
class PlaneWebhookFailure:
    category: Literal["retryable", "permanent"]
    message: str
    retry_after: datetime | None = None

class PlaneWebhookQueue(Protocol):
    def enqueue(self, event: dict[str, object]) -> PlaneWebhookEnqueueResult: ...
    def pending_events(self, limit: int) -> list[dict[str, object]]: ...
    def mark_dispatched(self, delivery_id: str) -> None: ...
    def mark_failed(self, delivery_id: str, failure: PlaneWebhookFailure) -> None: ...
    def replay_dead_letter(self, delivery_id: str) -> dict[str, object] | None: ...
    def status(self) -> PlaneWebhookQueueStatus: ...
```

Keep `FilePlaneWebhookQueue` behind this protocol so existing tests can still use temp files.

- [ ] **Step 4: Write failing Redis queue tests**

In `tests/test_plane_webhooks_redis.py`, test with a fake Redis client object instead of a live Redis server. Cover:

```python
def test_redis_queue_enqueue_dedupes_by_delivery_id(fake_redis): ...
def test_redis_queue_pending_skips_dispatched_and_dead_lettered(fake_redis): ...
def test_redis_queue_status_reports_pending_dispatched_retry_and_dead_letter_counts(fake_redis): ...
```

The fake should record Redis operations in memory and expose only the operations used by `RedisPlaneWebhookQueue`.

- [ ] **Step 5: Implement `RedisPlaneWebhookQueue`**

Use Redis keys under `plane_webhook_redis_prefix`:

```text
{prefix}:stream                  # Redis stream of normalized events
{prefix}:dedupe                  # set of idempotency keys already accepted
{prefix}:dispatched              # set of dispatched delivery IDs
{prefix}:retry                   # sorted set delivery ID -> next retry unix timestamp
{prefix}:dead_letter             # hash delivery ID -> JSON dead-letter record
{prefix}:events                  # hash delivery ID -> normalized event JSON
```

`enqueue()` must add the dedupe key first atomically enough for single-gateway operation, store the normalized event in `{prefix}:events`, append to `{prefix}:stream`, and return duplicate without appending when already present.

- [ ] **Step 6: Wire Compose/example env**

Add safe placeholders only:

```env
PLANE_WEBHOOK_QUEUE_BACKEND=redis
PLANE_WEBHOOK_REDIS_URL=redis://redis:6379/0
PLANE_WEBHOOK_REDIS_PREFIX=openclaw:plane:webhooks
```

If Redis is not already part of the gateway runtime stack, add a documented external dependency instead of inventing a new service unless the repo already has a Redis pattern for this app.

- [ ] **Step 7: Verify this task**

Run:

```bash
cd /home/oli/docker/apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_settings.py tests/test_plane_webhooks_redis.py -q
cd /home/oli/docker
docker compose -f apps/openclaw-gateway/compose.yml --env-file apps/openclaw-gateway/example.env config --quiet
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 8: Commit**

```bash
git add apps/openclaw-gateway/openclaw-gateway/pyproject.toml apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/settings.py apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/plane_webhooks.py apps/openclaw-gateway/openclaw-gateway/tests/test_settings.py apps/openclaw-gateway/openclaw-gateway/tests/test_plane_webhooks_redis.py apps/openclaw-gateway/compose.yml apps/openclaw-gateway/example.env
git commit -m "OPN-271: add Redis Plane webhook queue"
```

---

### Task 2: Full Normalized Event Envelope And Event Allowlist

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/plane_webhooks.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/workflow.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py`
- Modify: `apps/openclaw-gateway/README.md`
- Modify: `docs/workflow/plane.md`

**Interfaces:**
- Produces: `normalize_plane_webhook_event(payload, headers, raw_body, received_at) -> PlaneWebhookEnvelope`.
- Produces: allowlist decision for issue/work-item created, issue/work-item updated, issue/work-item state changed, and comment created.
- Produces: `ignored: true` response for unsupported event/action pairs without queueing.

- [ ] **Step 1: Add failing tests for the full envelope**

In `tests/test_workflow_routes.py`, add a signed webhook test asserting the queued event includes:

```python
{
    "schema_version": "plane.webhook.v1",
    "event_id": "delivery-1",
    "event_type": "work_item.created",
    "occurred_at": "2026-07-12T00:00:00Z",
    "received_at": ANY_ISO_TIMESTAMP,
    "plane_workspace_id": "workspace-1",
    "plane_project_id": "project-1",
    "plane_resource_type": "issue",
    "plane_resource_id": "issue-1",
    "work_item_identifier": "OPENCLAW-123",
    "actor": {"id": "user-1", "display_name": "Oli"},
    "source": "plane",
    "origin": "plane",
    "correlation_id": "plane:delivery-1",
    "causation_id": None,
    "raw_payload_hash": ANY_SHA256_HEX,
    "retry_attempt": 0,
    "payload": {"safe work item fields only": "..."},
}
```

Assert the raw body, `X-Plane-Signature`, webhook secret, and full raw `data` object are not persisted.

- [ ] **Step 2: Add failing allowlist tests**

Add tests for:

```python
issue.created -> queued, event_type == "work_item.created"
issue.updated with state change -> queued, event_type == "work_item.state_changed"
issue.updated without state change -> queued, event_type == "work_item.updated"
comment.created -> queued, event_type == "comment.created"
project.created -> accepted ignored, queued == False, ignored == True, ignored_reason == "unsupported_event"
```

- [ ] **Step 3: Implement envelope normalization**

Create helpers in `plane_webhooks.py`:

```python
def compute_raw_payload_hash(raw_body: bytes) -> str:
    return hashlib.sha256(raw_body).hexdigest()


def normalize_plane_webhook_event(
    payload: Mapping[str, object],
    *,
    delivery_id: str | None,
    raw_body: bytes,
    received_at: datetime,
) -> PlaneWebhookEnvelope:
    ...
```

Use `X-Plane-Delivery` when present. If absent, derive `event_id` from a stable hash of event/action/workspace/project/resource/timestamp/canonicalized safe payload.

- [ ] **Step 4: Implement allowlist filtering before enqueue**

Add a helper:

```python
def classify_plane_event(payload: Mapping[str, object]) -> PlaneWebhookEventClassification:
    ...
```

Return unsupported events as accepted-and-ignored. Log `correlation_id`, event, action, resource ID, and `ignored_reason` without secrets.

- [ ] **Step 5: Update response schemas**

Extend webhook response fields to include:

```python
ignored: bool = False
ignored_reason: str | None = None
event_type: str | None = None
schema_version: str | None = None
raw_payload_hash: str | None = None
```

- [ ] **Step 6: Verify this task**

Run:

```bash
cd /home/oli/docker/apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_workflow_routes.py -q
cd /home/oli/docker
docker compose -f apps/openclaw-gateway/compose.yml --env-file apps/openclaw-gateway/example.env config --quiet
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 7: Commit**

```bash
git add apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/plane_webhooks.py apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/workflow.py apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py apps/openclaw-gateway/README.md docs/workflow/plane.md
git commit -m "OPN-271: normalize and filter Plane webhook events"
```

---

### Task 3: Retry, Backoff, Failure Classification, And Dead Letter

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/plane_webhooks.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/n8n.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/workflow.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_n8n_client.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_plane_webhooks_redis.py`

**Interfaces:**
- Produces: retryable/permanent failure classification from n8n dispatch.
- Produces: exponential backoff with jitter and bounded attempts.
- Produces: dead-letter storage that is inspectable and replayable.

- [ ] **Step 1: Add failing tests for retryable failures**

Test that n8n timeout, connection error, and 5xx responses:

```python
assert response.status_code in {502, 504}
assert event["retry_attempt"] == 1
assert queue.status().retry_count == 1
assert queue.status().dead_letter_count == 0
```

The failed delivery must not be marked dispatched and must not be retried until its `next_retry_at` is due.

- [ ] **Step 2: Add failing tests for permanent failures**

Test that n8n/OpenClaw returns a structured permanent failure such as:

```json
{"ok": false, "failure_type": "permanent", "error_code": "invalid_idempotency_key"}
```

Expected: delivery moves directly to dead letter with `last_error_category == "permanent"` and is not retried by the next dispatch call.

- [ ] **Step 3: Add retry policy settings**

Add settings:

```python
plane_webhook_max_attempts: int = 5
plane_webhook_retry_base_seconds: int = 30
plane_webhook_retry_max_seconds: int = 1800
```

- [ ] **Step 4: Implement failure classification**

In `N8nClient.forward_plane_webhook_event()`, normalize failures into a result the route can classify:

```python
@dataclass(frozen=True)
class PlaneDispatchResult:
    ok: bool
    failure_type: Literal["retryable", "permanent"] | None = None
    error_code: str | None = None
    detail: str | None = None
```

Timeout, connection errors, and 5xx are retryable. 4xx from the dispatch workflow and explicit `failure_type=permanent` are permanent.

- [ ] **Step 5: Implement backoff and dead-letter transition**

Use capped exponential backoff:

```python
delay = min(base_seconds * (2 ** (attempt - 1)), max_seconds)
jitter = random.uniform(0, delay * 0.2)
next_retry_at = now + timedelta(seconds=delay + jitter)
```

When `attempt >= plane_webhook_max_attempts`, move to dead letter with the last error category and message.

- [ ] **Step 6: Verify this task**

Run:

```bash
cd /home/oli/docker/apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_n8n_client.py tests/test_workflow_routes.py tests/test_plane_webhooks_redis.py -q
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 7: Commit**

```bash
git add apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/plane_webhooks.py apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/clients/n8n.py apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/workflow.py apps/openclaw-gateway/openclaw-gateway/tests/test_n8n_client.py apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py apps/openclaw-gateway/openclaw-gateway/tests/test_plane_webhooks_redis.py
git commit -m "OPN-271: add Plane webhook retry and dead letter handling"
```

---

### Task 4: Queue Diagnostics, Replay, And Health Readiness

**Files:**
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/workflow.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_smoke_script.py`
- Modify: `scripts/smoke-openclaw-gateway.sh`
- Modify: `apps/openclaw-gateway/README.md`
- Modify: `docs/workflow/plane.md`

**Interfaces:**
- Produces: queue status response with retry/dead-letter counts and last successful dispatch timestamp.
- Produces: authenticated replay endpoint for dead-letter delivery IDs.
- Produces: readiness evidence for Redis and n8n dispatch configuration without mutating live state.

- [ ] **Step 1: Add failing diagnostics tests**

Extend `GET /v1/workflow/plane/webhook/queue` tests to assert:

```python
{
    "queued_count": 3,
    "pending_count": 1,
    "retry_count": 1,
    "dead_letter_count": 1,
    "last_successful_dispatch_at": "2026-07-12T01:00:00Z",
    "last_dead_letter_delivery_id": "delivery-dead"
}
```

- [ ] **Step 2: Add failing replay tests**

Add authenticated route tests for:

```text
POST /v1/workflow/plane/webhook/replay?delivery_id=delivery-dead
```

Expected behavior:

```python
assert response.status_code == 200
assert response.json()["replayed"] is True
assert response.json()["delivery_id"] == "delivery-dead"
assert queue.status().dead_letter_count == 0
assert queue.status().pending_count == 1
```

Missing delivery IDs return `404` with a secret-free error.

- [ ] **Step 3: Implement diagnostics schema and route updates**

Add fields to the queue status schema:

```python
retry_count: int
dead_letter_count: int
last_successful_dispatch_at: datetime | None
last_dead_letter_delivery_id: str | None
redis_configured: bool
redis_ready: bool | None
n8n_dispatch_configured: bool
```

Do not include raw queued payloads.

- [ ] **Step 4: Implement replay route**

Add authenticated route:

```text
POST /v1/workflow/plane/webhook/replay?delivery_id=<id>
```

It must move the dead-letter event back to pending with incremented replay metadata, not immediately dispatch it.

- [ ] **Step 5: Update smoke script optional field checks**

When `CHECK_PLANE_WEBHOOK_QUEUE=1`, require these non-secret fields:

```text
queued_count
pending_count
dispatched_count
retry_count
dead_letter_count
malformed_count
redis_configured
n8n_dispatch_configured
```

- [ ] **Step 6: Verify this task**

Run:

```bash
cd /home/oli/docker/apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_workflow_routes.py tests/test_smoke_script.py -q
cd /home/oli/docker
docker compose -f apps/openclaw-gateway/compose.yml --env-file apps/openclaw-gateway/example.env config --quiet
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 7: Commit**

```bash
git add apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/routers/workflow.py apps/openclaw-gateway/openclaw-gateway/openclaw_gateway/schemas/workflow.py apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py apps/openclaw-gateway/openclaw-gateway/tests/test_smoke_script.py scripts/smoke-openclaw-gateway.sh apps/openclaw-gateway/README.md docs/workflow/plane.md
git commit -m "OPN-271: expose Plane webhook dead letter diagnostics"
```

---

### Task 5: Dispatch Contract Hardening And Origin Markers

**Files:**
- Modify: `apps/utilities/n8n/scripts/send-plane-openclaw-dispatch.sh`
- Modify: `apps/utilities/n8n/scripts/test-send-plane-openclaw-dispatch.js`
- Modify: `apps/utilities/n8n/workflows/plane-openclaw-dispatch.workflow.json`
- Modify: `apps/utilities/n8n/scripts/test-plane-openclaw-dispatch-workflow.js`
- Modify: `apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py`
- Modify: `apps/openclaw-gateway/README.md`
- Modify: `docs/workflow/plane.md`

**Interfaces:**
- Consumes: normalized envelope from Task 2.
- Produces: n8n/OpenClaw dispatch payload with idempotency key, correlation ID, causation ID, origin marker, retry attempt, and explicit success/failure contract.
- Produces: documented actor-ID loop prevention plus comment/body origin marker strategy where practical.

- [ ] **Step 1: Add failing n8n sender tests for contract fields**

Update sender tests to assert the uploaded payload includes:

```json
{
  "schema_version": "plane.webhook.v1",
  "event_id": "delivery-1",
  "event_type": "work_item.updated",
  "idempotency_key": "delivery-1",
  "correlation_id": "plane:delivery-1",
  "causation_id": null,
  "origin": "plane",
  "retry_attempt": 0,
  "raw_payload_hash": "<sha256>"
}
```

Assert no raw Plane payload, signature header, webhook secret, gateway token, or SSH key material is printed.

- [ ] **Step 2: Add failing workflow response tests**

The n8n workflow template should return one of:

```json
{"ok": true, "correlation_id": "plane:delivery-1"}
{"ok": false, "failure_type": "retryable", "error_code": "ssh_timeout"}
{"ok": false, "failure_type": "permanent", "error_code": "invalid_event"}
```

- [ ] **Step 3: Harden sender script payload and response mapping**

Ensure the script passes only normalized fields and maps OpenClaw command exit categories into the JSON contract above. If the existing command cannot emit structured failure JSON, map non-zero exit to retryable by default and document that OpenClaw must later emit permanent failure codes for validation errors.

- [ ] **Step 4: Document auth boundary and origin strategy**

Document:

```text
n8n authenticates to OpenClaw via SSH key mounted outside Git.
The SSH key must be scoped to the dispatch command where possible.
Actor-ID suppression remains primary loop prevention.
OpenClaw/Codex/n8n write-backs should include a textual origin marker such as [openclaw-origin:<correlation_id>] in Plane comments where the write surface supports it.
```

- [ ] **Step 5: Verify this task**

Run:

```bash
cd /home/oli/docker
node apps/utilities/n8n/scripts/test-send-plane-openclaw-dispatch.js
node apps/utilities/n8n/scripts/test-plane-openclaw-dispatch-workflow.js
cd /home/oli/docker/apps/openclaw-gateway/openclaw-gateway
python -m pytest tests/test_workflow_routes.py -q
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 6: Commit**

```bash
git add apps/utilities/n8n/scripts/send-plane-openclaw-dispatch.sh apps/utilities/n8n/scripts/test-send-plane-openclaw-dispatch.js apps/utilities/n8n/workflows/plane-openclaw-dispatch.workflow.json apps/utilities/n8n/scripts/test-plane-openclaw-dispatch-workflow.js apps/openclaw-gateway/openclaw-gateway/tests/test_workflow_routes.py apps/openclaw-gateway/README.md docs/workflow/plane.md
git commit -m "OPN-271: harden Plane dispatch contract"
```

---

### Task 6: Final Verification, Live Smoke Checklist, And Linear Evidence

**Files:**
- Modify: `apps/openclaw-gateway/README.md`
- Modify: `docs/workflow/plane.md`
- Modify: `docs/superpowers/plans/2026-07-12-opn-271-plane-webhook-desired-state.md`

**Interfaces:**
- Produces: documented final smoke sequence and rollback procedure aligned with OPN-271 Definition of Done.
- Produces: Linear update evidence after live checks are actually run.

- [ ] **Step 1: Run local regression verification**

Run:

```bash
cd /home/oli/docker/apps/openclaw-gateway/openclaw-gateway
python -m pytest -q
cd /home/oli/docker
node apps/utilities/n8n/scripts/test-send-plane-openclaw-dispatch.js
node apps/utilities/n8n/scripts/test-plane-openclaw-dispatch-workflow.js
docker compose -f apps/openclaw-gateway/compose.yml --env-file apps/openclaw-gateway/example.env config --quiet
docker compose -f apps/utilities/compose.yml --env-file apps/utilities/example.env config --quiet
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 2: Run a focused changed-file secret scan**

Run a targeted scan of changed files only. Expected findings are limited to placeholder names, env variable names, test constants, UUIDs, and fixed paths. If any real credential or raw secret-like runtime value appears, stop and remove it before continuing.

- [ ] **Step 3: Prepare Komodo deployment checklist**

Document these required external steps without performing live mutation unless explicitly approved:

```text
1. Confirm backup/checkpoint coverage for gateway appdata and Redis persistence.
2. Configure Redis availability for the gateway runtime.
3. Configure real `PLANE_WEBHOOK_SECRET` outside Git.
4. Configure real `PLANE_WEBHOOK_IGNORED_ACTOR_IDS` outside Git.
5. Import/enable or update n8n `plane-openclaw-dispatch` workflow.
6. Confirm n8n SSH key scope and `OPENCLAW_PLANE_DISPATCH_COMMAND` on the OpenClaw host.
7. Redeploy through Komodo.
```

- [ ] **Step 4: Run live smoke only after approval**

After explicit approval and Komodo deployment, run the OPN-271 smoke sequence:

```text
1. Confirm `/health` and readiness are healthy.
2. Trigger one test Plane issue update.
3. Confirm webhook accepted.
4. Confirm one normalized event queued in Redis.
5. Confirm one n8n -> OpenClaw dispatch with correlation propagation.
6. Confirm one Plane/OpenClaw audit trail.
7. Re-send the same payload and confirm no duplicate action.
8. Trigger a write-back event and confirm no loop.
9. Simulate downstream retryable failure and confirm backoff retry state.
10. Simulate permanent or exhausted failure and confirm dead-letter visibility.
11. Replay a dead-letter event and confirm it returns to pending without direct Redis access.
12. Disable any test webhook after verification.
```

Do not mark OPN-271 Done until steps 8-11 are evidenced.

- [ ] **Step 5: Update Linear with final evidence**

Add a final OPN-271 comment containing:

```text
Outcome: done or blocked.
What changed: Redis queue, full envelope, allowlist, retry/backoff, dead-letter/replay, dispatch contract hardening.
Verification: exact local commands and live smoke results.
Deployment: Komodo deployment reference if performed.
Rollback: disable Plane webhook, stop worker/dispatch schedule, retain Redis queue/dead-letter keys, restore Linear path until OPN-276 cutover.
Remaining follow-ups: None, or exact owners/actions.
```

- [ ] **Step 6: Commit docs finalization**

```bash
git add apps/openclaw-gateway/README.md docs/workflow/plane.md docs/superpowers/plans/2026-07-12-opn-271-plane-webhook-desired-state.md
git commit -m "OPN-271: document Plane webhook desired state verification"
```
