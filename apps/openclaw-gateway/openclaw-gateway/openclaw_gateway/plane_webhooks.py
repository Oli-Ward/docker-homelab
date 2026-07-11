import json
from pathlib import Path
from threading import Lock
from typing import Any


_queue_locks: dict[Path, Lock] = {}
_queue_locks_guard = Lock()


class PlaneWebhookQueueError(Exception):
    pass


class FilePlaneWebhookQueue:
    def __init__(self, queue_path: str, dedupe_path: str | None = None) -> None:
        self.queue_path = Path(queue_path)
        self.dedupe_path = Path(dedupe_path) if dedupe_path else self.queue_path.with_suffix(
            f"{self.queue_path.suffix}.seen"
        )

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
