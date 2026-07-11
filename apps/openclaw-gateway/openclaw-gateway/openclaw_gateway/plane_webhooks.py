import json
from pathlib import Path
from threading import Lock
from typing import Any

from pydantic import BaseModel


_queue_locks: dict[Path, Lock] = {}
_queue_locks_guard = Lock()


class PlaneWebhookQueueError(Exception):
    pass


class PlaneWebhookQueueStatus(BaseModel):
    configured: bool
    queue_path: str
    dedupe_path: str
    queued_count: int
    dedupe_count: int
    malformed_count: int
    last_delivery_id: str | None = None
    last_correlation_id: str | None = None


class FilePlaneWebhookQueue:
    def __init__(self, queue_path: str, dedupe_path: str | None = None) -> None:
        self.queue_path = Path(queue_path)
        self.dedupe_path = Path(dedupe_path) if dedupe_path else self.queue_path.with_suffix(
            f"{self.queue_path.suffix}.seen"
        )
        self.dispatched_path = self.queue_path.with_suffix(f"{self.queue_path.suffix}.dispatched")

    def enqueue(self, delivery_id: str, event: dict[str, Any]) -> bool:
        try:
            with self._lock():
                seen = self._read_seen_delivery_ids()
                if delivery_id in seen:
                    return False

                self.queue_path.parent.mkdir(parents=True, exist_ok=True)
                self.dedupe_path.parent.mkdir(parents=True, exist_ok=True)
                with self.queue_path.open("a", encoding="utf-8") as queue_file:
                    queue_file.write(json.dumps(event, separators=(",", ":"), sort_keys=True))
                    queue_file.write("\n")
                with self.dedupe_path.open("a", encoding="utf-8") as dedupe_file:
                    dedupe_file.write(delivery_id)
                    dedupe_file.write("\n")
                return True
        except OSError as exc:
            raise PlaneWebhookQueueError(str(exc)) from exc

    def pending_events(self, limit: int) -> list[dict[str, object]]:
        try:
            with self._lock():
                dispatched_delivery_ids = self._read_dispatched_delivery_ids()
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
        except OSError as exc:
            raise PlaneWebhookQueueError(str(exc)) from exc

    def status(self, configured: bool = True) -> PlaneWebhookQueueStatus:
        try:
            with self._lock():
                queued_count = 0
                malformed_count = 0
                last_delivery_id: str | None = None
                last_correlation_id: str | None = None
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
                        last_delivery_id = delivery_id if isinstance(delivery_id, str) else None
                        last_correlation_id = correlation_id if isinstance(correlation_id, str) else None

                return PlaneWebhookQueueStatus(
                    configured=configured,
                    queue_path=str(self.queue_path),
                    dedupe_path=str(self.dedupe_path),
                    queued_count=queued_count,
                    dedupe_count=len(self._read_seen_delivery_ids()),
                    malformed_count=malformed_count,
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
