import json
import hashlib
from pathlib import Path
from threading import Lock
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Protocol

from pydantic import BaseModel


_queue_locks: dict[Path, Lock] = {}
_queue_locks_guard = Lock()


class PlaneWebhookQueueError(Exception):
    pass


@dataclass(frozen=True)
class PlaneWebhookEventClassification:
    supported: bool
    event_type: str | None
    ignored_reason: str | None = None


@dataclass(frozen=True)
class PlaneWebhookEnqueueResult:
    queued: bool
    duplicate: bool


@dataclass(frozen=True)
class PlaneWebhookFailure:
    category: Literal["retryable", "permanent"]
    message: str
    retry_after: datetime | None = None


class PlaneWebhookQueueStatus(BaseModel):
    configured: bool
    queue_path: str
    dedupe_path: str
    queued_count: int
    dedupe_count: int
    dispatched_count: int
    pending_count: int
    malformed_count: int
    retry_count: int = 0
    dead_letter_count: int = 0
    last_successful_dispatch_at: datetime | None = None
    last_dead_letter_delivery_id: str | None = None
    redis_configured: bool = False
    redis_ready: bool | None = None
    n8n_dispatch_configured: bool = False
    last_delivery_id: str | None = None
    last_correlation_id: str | None = None


class PlaneWebhookQueue(Protocol):
    def enqueue(self, event: dict[str, object]) -> PlaneWebhookEnqueueResult: ...
    def pending_events(self, limit: int) -> list[dict[str, object]]: ...
    def mark_dispatched(self, delivery_id: str) -> None: ...
    def mark_failed(self, delivery_id: str, failure: PlaneWebhookFailure) -> None: ...
    def replay_dead_letter(self, delivery_id: str) -> dict[str, object] | None: ...
    def status(self, configured: bool = True, n8n_dispatch_configured: bool = False) -> PlaneWebhookQueueStatus: ...


class FilePlaneWebhookQueue:
    def __init__(self, queue_path: str, dedupe_path: str | None = None) -> None:
        self.queue_path = Path(queue_path)
        self.dedupe_path = Path(dedupe_path) if dedupe_path else self.queue_path.with_suffix(
            f"{self.queue_path.suffix}.seen"
        )
        self.dispatched_path = self.queue_path.with_suffix(f"{self.queue_path.suffix}.dispatched")

    def enqueue(
        self,
        event: dict[str, object],
        delivery_id: str | None = None,
    ) -> PlaneWebhookEnqueueResult:
        resolved_delivery_id = delivery_id or event.get("delivery_id") or event.get("event_id")
        if not isinstance(resolved_delivery_id, str) or not resolved_delivery_id:
            raise PlaneWebhookQueueError("missing delivery id")
        try:
            with self._lock():
                seen = self._read_seen_delivery_ids()
                if resolved_delivery_id in seen:
                    return PlaneWebhookEnqueueResult(queued=False, duplicate=True)

                self.queue_path.parent.mkdir(parents=True, exist_ok=True)
                self.dedupe_path.parent.mkdir(parents=True, exist_ok=True)
                with self.queue_path.open("a", encoding="utf-8") as queue_file:
                    queue_file.write(json.dumps(event, separators=(",", ":"), sort_keys=True))
                    queue_file.write("\n")
                with self.dedupe_path.open("a", encoding="utf-8") as dedupe_file:
                    dedupe_file.write(resolved_delivery_id)
                    dedupe_file.write("\n")
                return PlaneWebhookEnqueueResult(queued=True, duplicate=False)
        except OSError as exc:
            raise PlaneWebhookQueueError(str(exc)) from exc

    def pending_events(self, limit: int) -> list[dict[str, object]]:
        try:
            with self._lock():
                dispatched_delivery_ids = self._read_dispatched_delivery_ids()
                failures = self._read_failures()
                now = datetime.now(timezone.utc)
                events: list[dict[str, object]] = []
                if not self.queue_path.exists():
                    return events
                for line in self.queue_path.read_text(encoding="utf-8").splitlines():
                    if len(events) >= limit:
                        break
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(event, dict):
                        continue
                    delivery_id = event.get("delivery_id")
                    if not isinstance(delivery_id, str) or delivery_id in dispatched_delivery_ids:
                        continue
                    failure = failures.get(delivery_id)
                    if failure and failure.get("category") == "permanent":
                        continue
                    retry_after = _parse_datetime(failure.get("retry_after") if failure else None)
                    if retry_after and retry_after > now:
                        continue
                    events.append(event)
                return events
        except OSError as exc:
            raise PlaneWebhookQueueError(str(exc)) from exc

    def mark_dispatched(self, delivery_id: str) -> None:
        try:
            with self._lock():
                self.dispatched_path.parent.mkdir(parents=True, exist_ok=True)
                dispatched_delivery_ids = self._read_dispatched_delivery_ids()
                if delivery_id in dispatched_delivery_ids:
                    return
                with self.dispatched_path.open("a", encoding="utf-8") as dispatched_file:
                    dispatched_file.write(delivery_id)
                    dispatched_file.write("\n")
                failures = self._read_failures()
                if failures.pop(delivery_id, None) is not None:
                    self._write_json_map(self.failure_path, failures)
                self._write_last_successful_dispatch_at(datetime.now(timezone.utc))
        except OSError as exc:
            raise PlaneWebhookQueueError(str(exc)) from exc

    def mark_failed(self, delivery_id: str, failure: PlaneWebhookFailure) -> None:
        try:
            with self._lock():
                failures = self._read_failures()
                failures[delivery_id] = {
                    "category": failure.category,
                    "message": failure.message,
                    "retry_after": _format_datetime(failure.retry_after) if failure.retry_after else None,
                    "recorded_at": _format_datetime(datetime.now(timezone.utc)),
                }
                self._write_json_map(self.failure_path, failures)
        except OSError as exc:
            raise PlaneWebhookQueueError(str(exc)) from exc

    def replay_dead_letter(self, delivery_id: str) -> dict[str, object] | None:
        try:
            with self._lock():
                failures = self._read_failures()
                failure = failures.get(delivery_id)
                if not failure or failure.get("category") != "permanent":
                    return None
                event = self._read_event(delivery_id)
                if event is None:
                    return None
                failures.pop(delivery_id, None)
                self._write_json_map(self.failure_path, failures)
                event["replay_count"] = int(event.get("replay_count", 0) or 0) + 1
                return event
        except OSError as exc:
            raise PlaneWebhookQueueError(str(exc)) from exc

    def status(self, configured: bool = True, n8n_dispatch_configured: bool = False) -> PlaneWebhookQueueStatus:
        try:
            with self._lock():
                queued_count = 0
                pending_count = 0
                malformed_count = 0
                last_delivery_id: str | None = None
                last_correlation_id: str | None = None
                dispatched_delivery_ids = self._read_dispatched_delivery_ids()
                failures = self._read_failures()
                now = datetime.now(timezone.utc)
                if self.queue_path.exists():
                    for line in self.queue_path.read_text(encoding="utf-8").splitlines():
                        if not line.strip():
                            continue
                        try:
                            event = json.loads(line)
                        except json.JSONDecodeError:
                            malformed_count += 1
                            continue
                        if not isinstance(event, dict):
                            malformed_count += 1
                            continue
                        queued_count += 1
                        delivery_id = event.get("delivery_id")
                        correlation_id = event.get("correlation_id")
                        if isinstance(delivery_id, str) and delivery_id not in dispatched_delivery_ids:
                            failure = failures.get(delivery_id)
                            retry_after = _parse_datetime(failure.get("retry_after") if failure else None)
                            if not failure or (
                                failure.get("category") == "retryable"
                                and (retry_after is None or retry_after <= now)
                            ):
                                pending_count += 1
                        last_delivery_id = delivery_id if isinstance(delivery_id, str) else None
                        last_correlation_id = correlation_id if isinstance(correlation_id, str) else None
                dead_letters = [
                    delivery_id
                    for delivery_id, failure in failures.items()
                    if failure.get("category") == "permanent"
                ]
                retry_count = sum(
                    1
                    for failure in failures.values()
                    if failure.get("category") == "retryable"
                )

                return PlaneWebhookQueueStatus(
                    configured=configured,
                    queue_path=str(self.queue_path),
                    dedupe_path=str(self.dedupe_path),
                    queued_count=queued_count,
                    dedupe_count=len(self._read_seen_delivery_ids()),
                    dispatched_count=len(dispatched_delivery_ids),
                    pending_count=pending_count,
                    malformed_count=malformed_count,
                    retry_count=retry_count,
                    dead_letter_count=len(dead_letters),
                    last_successful_dispatch_at=self._read_last_successful_dispatch_at(),
                    last_dead_letter_delivery_id=dead_letters[-1] if dead_letters else None,
                    n8n_dispatch_configured=n8n_dispatch_configured,
                    last_delivery_id=last_delivery_id,
                    last_correlation_id=last_correlation_id,
                )
        except OSError as exc:
            raise PlaneWebhookQueueError(str(exc)) from exc

    def _lock(self) -> Lock:
        with _queue_locks_guard:
            return _queue_locks.setdefault(self.queue_path, Lock())

    def _read_seen_delivery_ids(self) -> set[str]:
        delivery_ids: set[str] = set()
        if self.dedupe_path.exists():
            delivery_ids.update(
                line.strip()
                for line in self.dedupe_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        if self.queue_path.exists():
            for line in self.queue_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                delivery_id = event.get("delivery_id") if isinstance(event, dict) else None
                if isinstance(delivery_id, str):
                    delivery_ids.add(delivery_id)
        return delivery_ids

    def _read_dispatched_delivery_ids(self) -> set[str]:
        if not self.dispatched_path.exists():
            return set()
        return {
            line.strip()
            for line in self.dispatched_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }

    @property
    def failure_path(self) -> Path:
        return self.queue_path.with_suffix(f"{self.queue_path.suffix}.failures.json")

    @property
    def last_successful_dispatch_path(self) -> Path:
        return self.queue_path.with_suffix(f"{self.queue_path.suffix}.last-dispatch")

    def _read_failures(self) -> dict[str, dict[str, object]]:
        if not self.failure_path.exists():
            return {}
        payload = json.loads(self.failure_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {}
        return {
            str(delivery_id): failure
            for delivery_id, failure in payload.items()
            if isinstance(failure, dict)
        }

    def _write_json_map(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _read_event(self, delivery_id: str) -> dict[str, object] | None:
        if not self.queue_path.exists():
            return None
        for line in self.queue_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict) and event.get("delivery_id") == delivery_id:
                return event
        return None

    def _write_last_successful_dispatch_at(self, timestamp: datetime) -> None:
        self.last_successful_dispatch_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_successful_dispatch_path.write_text(_format_datetime(timestamp), encoding="utf-8")

    def _read_last_successful_dispatch_at(self) -> datetime | None:
        if not self.last_successful_dispatch_path.exists():
            return None
        return _parse_datetime(self.last_successful_dispatch_path.read_text(encoding="utf-8").strip())


class RedisPlaneWebhookQueue:
    def __init__(self, redis_client: Any, prefix: str) -> None:
        self.redis = redis_client
        self.prefix = prefix.rstrip(":")

    def enqueue(self, event: dict[str, object]) -> PlaneWebhookEnqueueResult:
        delivery_id = _event_delivery_id(event)
        try:
            if self.redis.sadd(self._key("dedupe"), delivery_id) == 0:
                return PlaneWebhookEnqueueResult(queued=False, duplicate=True)
            serialized = json.dumps(event, separators=(",", ":"), sort_keys=True)
            self.redis.hset(self._key("events"), delivery_id, serialized)
            self.redis.xadd(self._key("stream"), {"delivery_id": delivery_id, "event": serialized})
            return PlaneWebhookEnqueueResult(queued=True, duplicate=False)
        except Exception as exc:  # noqa: BLE001 - Redis clients expose multiple runtime errors.
            raise PlaneWebhookQueueError(str(exc)) from exc

    def pending_events(self, limit: int) -> list[dict[str, object]]:
        try:
            now = datetime.now(timezone.utc).timestamp()
            events: list[dict[str, object]] = []
            for delivery_id, serialized in self.redis.hgetall(self._key("events")).items():
                delivery_id = _decode_redis_value(delivery_id)
                if self.redis.sismember(self._key("dispatched"), delivery_id):
                    continue
                if self.redis.hget(self._key("dead_letter"), delivery_id) is not None:
                    continue
                retry_at = self.redis.zscore(self._key("retry"), delivery_id)
                if retry_at is not None and float(retry_at) > now:
                    continue
                event = json.loads(_decode_redis_value(serialized))
                if not isinstance(event, dict):
                    continue
                events.append(event)
                if len(events) >= limit:
                    break
            return events
        except Exception as exc:  # noqa: BLE001
            raise PlaneWebhookQueueError(str(exc)) from exc

    def mark_dispatched(self, delivery_id: str) -> None:
        try:
            self.redis.sadd(self._key("dispatched"), delivery_id)
            self.redis.zrem(self._key("retry"), delivery_id)
            self.redis.hset(
                self._key("meta"),
                "last_successful_dispatch_at",
                _format_datetime(datetime.now(timezone.utc)),
            )
        except Exception as exc:  # noqa: BLE001
            raise PlaneWebhookQueueError(str(exc)) from exc

    def mark_failed(self, delivery_id: str, failure: PlaneWebhookFailure) -> None:
        try:
            record = {
                "delivery_id": delivery_id,
                "category": failure.category,
                "message": failure.message,
                "retry_after": _format_datetime(failure.retry_after) if failure.retry_after else None,
                "recorded_at": _format_datetime(datetime.now(timezone.utc)),
            }
            if failure.category == "permanent":
                self.redis.hset(
                    self._key("dead_letter"),
                    delivery_id,
                    json.dumps(record, separators=(",", ":"), sort_keys=True),
                )
                self.redis.zrem(self._key("retry"), delivery_id)
                self.redis.hset(self._key("meta"), "last_dead_letter_delivery_id", delivery_id)
                return
            retry_after = failure.retry_after or datetime.now(timezone.utc)
            self.redis.zadd(self._key("retry"), {delivery_id: retry_after.timestamp()})
            self.redis.hset(
                self._key("failures"),
                delivery_id,
                json.dumps(record, separators=(",", ":"), sort_keys=True),
            )
        except Exception as exc:  # noqa: BLE001
            raise PlaneWebhookQueueError(str(exc)) from exc

    def replay_dead_letter(self, delivery_id: str) -> dict[str, object] | None:
        try:
            if self.redis.hget(self._key("dead_letter"), delivery_id) is None:
                return None
            serialized = self.redis.hget(self._key("events"), delivery_id)
            if serialized is None:
                return None
            self.redis.hdel(self._key("dead_letter"), delivery_id)
            self.redis.zrem(self._key("retry"), delivery_id)
            event = json.loads(_decode_redis_value(serialized))
            if not isinstance(event, dict):
                return None
            event["replay_count"] = int(event.get("replay_count", 0) or 0) + 1
            self.redis.hset(
                self._key("events"),
                delivery_id,
                json.dumps(event, separators=(",", ":"), sort_keys=True),
            )
            return event
        except Exception as exc:  # noqa: BLE001
            raise PlaneWebhookQueueError(str(exc)) from exc

    def status(self, configured: bool = True, n8n_dispatch_configured: bool = False) -> PlaneWebhookQueueStatus:
        try:
            total_events = self.redis.hlen(self._key("events"))
            dispatched_count = self.redis.scard(self._key("dispatched"))
            retry_count = self.redis.zcard(self._key("retry"))
            dead_letter_count = self.redis.hlen(self._key("dead_letter"))
            pending_count = len(self.pending_events(limit=max(total_events, 1)))
            return PlaneWebhookQueueStatus(
                configured=configured,
                queue_path=self._key("stream"),
                dedupe_path=self._key("dedupe"),
                queued_count=total_events,
                dedupe_count=self.redis.scard(self._key("dedupe")),
                dispatched_count=dispatched_count,
                pending_count=pending_count,
                malformed_count=0,
                retry_count=retry_count,
                dead_letter_count=dead_letter_count,
                last_successful_dispatch_at=_parse_datetime(
                    _decode_optional_redis_value(
                        self.redis.hget(self._key("meta"), "last_successful_dispatch_at")
                    )
                ),
                last_dead_letter_delivery_id=_decode_optional_redis_value(
                    self.redis.hget(self._key("meta"), "last_dead_letter_delivery_id")
                ),
                redis_configured=True,
                redis_ready=True,
                n8n_dispatch_configured=n8n_dispatch_configured,
            )
        except Exception as exc:  # noqa: BLE001
            raise PlaneWebhookQueueError(str(exc)) from exc

    def _key(self, suffix: str) -> str:
        return f"{self.prefix}:{suffix}"


def _event_delivery_id(event: dict[str, object]) -> str:
    delivery_id = event.get("delivery_id") or event.get("event_id")
    if not isinstance(delivery_id, str) or not delivery_id:
        raise PlaneWebhookQueueError("missing delivery id")
    return delivery_id


def _decode_redis_value(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _decode_optional_redis_value(value: object | None) -> str | None:
    if value is None:
        return None
    return _decode_redis_value(value)


def _format_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: object | None) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def compute_raw_payload_hash(raw_body: bytes) -> str:
    return hashlib.sha256(raw_body).hexdigest()


def classify_plane_event(payload: dict[str, object]) -> PlaneWebhookEventClassification:
    event = _string(payload.get("event")).lower()
    action = _string(payload.get("action")).lower()
    resource, event_action = _split_plane_event(event, action)

    if resource in {"issue", "work_item", "work-item", "workitem"}:
        if event_action in {"created", "create"}:
            return PlaneWebhookEventClassification(True, "work_item.created")
        if event_action in {"updated", "update"}:
            if _looks_like_state_change(payload):
                return PlaneWebhookEventClassification(True, "work_item.state_changed")
            return PlaneWebhookEventClassification(True, "work_item.updated")

    if resource in {"comment", "issue_comment", "issue-comment"} and event_action in {"created", "create"}:
        return PlaneWebhookEventClassification(True, "comment.created")

    return PlaneWebhookEventClassification(False, None, "unsupported_event")


def normalize_plane_webhook_event(
    payload: dict[str, object],
    *,
    delivery_id: str | None,
    raw_body: bytes,
    received_at: datetime,
) -> dict[str, object]:
    classification = classify_plane_event(payload)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    assert isinstance(data, dict)
    safe_payload = _safe_work_item_metadata(data)
    event_id = delivery_id or _derived_event_id(payload, safe_payload)
    correlation_id = f"plane:{event_id}"
    raw_hash = compute_raw_payload_hash(raw_body)
    actor_id, actor_name = _actor(payload)
    resource_id = _string(data.get("id"))
    project_id = _string(data.get("project_id")) or _string(data.get("project"))
    workspace_id = _string(payload.get("workspace_id")) or _object_string(payload.get("workspace"), "id")
    resource, _ = _split_plane_event(_string(payload.get("event")).lower(), _string(payload.get("action")).lower())
    resource_type = "comment" if "comment" in resource else "issue"
    occurred_at = (
        _string(payload.get("created_at"))
        or _string(payload.get("updated_at"))
        or _string(payload.get("timestamp"))
        or _format_datetime(received_at)
    )
    envelope: dict[str, object] = {
        "schema_version": "plane.webhook.v1",
        "event_id": event_id,
        "delivery_id": event_id,
        "event": payload.get("event") if isinstance(payload.get("event"), str) else None,
        "action": payload.get("action") if isinstance(payload.get("action"), str) else None,
        "event_type": classification.event_type,
        "occurred_at": occurred_at,
        "received_at": _format_datetime(received_at),
        "plane_workspace_id": workspace_id,
        "plane_project_id": project_id,
        "plane_resource_type": resource_type,
        "plane_resource_id": resource_id,
        "work_item_identifier": safe_payload.get("source_identifier"),
        "actor": {"id": actor_id, "display_name": actor_name},
        "source": "plane",
        "origin": "plane",
        "correlation_id": correlation_id,
        "causation_id": None,
        "raw_payload_hash": raw_hash,
        "retry_attempt": int(payload.get("retry_attempt", 0) or 0),
        "payload": safe_payload,
        "resource_id": resource_id,
        "webhook_id": payload.get("webhook_id") if isinstance(payload.get("webhook_id"), str) else None,
    }
    envelope.update(safe_payload)
    if actor_id:
        envelope["actor_id"] = actor_id
    return envelope


def _safe_work_item_metadata(data: dict[str, object]) -> dict[str, object]:
    metadata: dict[str, object] = {}
    for source_key, target_key in (
        ("project_id", "project_id"),
        ("project", "project_id"),
        ("team", "team"),
        ("team_name", "team"),
        ("teamName", "team"),
        ("source_identifier", "source_identifier"),
        ("sourceIdentifier", "source_identifier"),
        ("name", "name"),
        ("state_id", "state_id"),
        ("state", "state_id"),
        ("priority", "priority"),
    ):
        value = _string(data.get(source_key))
        if value and target_key not in metadata:
            metadata[target_key] = value

    sequence_id = data.get("sequence_id")
    if isinstance(sequence_id, int) and not isinstance(sequence_id, bool):
        metadata["sequence_id"] = sequence_id

    state = data.get("state")
    if isinstance(state, dict):
        state_id = _string(state.get("id"))
        state_name = _string(state.get("name"))
        if state_id:
            metadata["state_id"] = state_id
        if state_name:
            metadata["state_name"] = state_name

    labels = data.get("labels") or data.get("label_details")
    if isinstance(labels, list):
        names = []
        for label in labels:
            if isinstance(label, str) and label:
                names.append(label)
            elif isinstance(label, dict):
                name = _string(label.get("name"))
                if name:
                    names.append(name)
        if names:
            metadata["label_names"] = names
    agent_ready = data.get("agent_ready") or data.get("agentReady")
    if isinstance(agent_ready, dict):
        checks: dict[str, bool] = {}
        for key, value in agent_ready.items():
            check_name = _string(key)
            if check_name:
                checks[check_name] = bool(value)
        if checks:
            metadata["agent_ready"] = checks

    agent_ready_checks = data.get("agent_ready_checks") or data.get("agentReadyChecks")
    if isinstance(agent_ready_checks, list):
        checks = [_string(check).strip() for check in agent_ready_checks]
        checks = [check for check in checks if check]
        if checks:
            metadata["agent_ready_checks"] = checks
    return metadata


def _split_plane_event(event: str, action: str) -> tuple[str, str]:
    if "." in event:
        resource, event_action = event.split(".", 1)
        return resource, event_action
    return event, action


def _looks_like_state_change(payload: dict[str, object]) -> bool:
    data = payload.get("data")
    if isinstance(data, dict) and ("state_id" in data or "state" in data):
        return True
    for field in ("changes", "changed_fields", "updated_fields"):
        value = payload.get(field)
        if isinstance(value, dict) and any(key in value for key in ("state", "state_id")):
            return True
        if isinstance(value, list) and any(item in {"state", "state_id"} for item in value):
            return True
    return False


def _actor(payload: dict[str, object]) -> tuple[str | None, str | None]:
    for field_name in ("actor", "updated_by", "created_by", "owned_by"):
        actor = payload.get(field_name)
        if isinstance(actor, dict):
            actor_id = _string(actor.get("id"))
            actor_name = _string(actor.get("display_name")) or _string(actor.get("name"))
            return actor_id, actor_name
        if isinstance(actor, str) and actor:
            return actor, None
    return None, None


def _object_string(value: object, key: str) -> str | None:
    if isinstance(value, dict):
        return _string(value.get(key))
    return None


def _string(value: object) -> str:
    return value if isinstance(value, str) else ""


def _derived_event_id(payload: dict[str, object], safe_payload: dict[str, object]) -> str:
    canonical = json.dumps(
        {
            "event": payload.get("event"),
            "action": payload.get("action"),
            "workspace_id": payload.get("workspace_id"),
            "data_id": payload.get("data", {}).get("id") if isinstance(payload.get("data"), dict) else None,
            "payload": safe_payload,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
