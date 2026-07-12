from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from openclaw_gateway.plane_webhooks import (
    PlaneWebhookFailure,
    RedisPlaneWebhookQueue,
)


class FakeRedis:
    def __init__(self) -> None:
        self.sets: dict[str, set[str]] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.streams: dict[str, list[dict[str, str]]] = {}
        self.sorted_sets: dict[str, dict[str, float]] = {}

    def sadd(self, key: str, value: str) -> int:
        values = self.sets.setdefault(key, set())
        if value in values:
            return 0
        values.add(value)
        return 1

    def sismember(self, key: str, value: str) -> bool:
        return value in self.sets.get(key, set())

    def scard(self, key: str) -> int:
        return len(self.sets.get(key, set()))

    def hset(self, key: str, name: str, value: str) -> int:
        self.hashes.setdefault(key, {})[name] = value
        return 1

    def hget(self, key: str, name: str) -> str | None:
        return self.hashes.get(key, {}).get(name)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    def hdel(self, key: str, name: str) -> int:
        return 1 if self.hashes.get(key, {}).pop(name, None) is not None else 0

    def hlen(self, key: str) -> int:
        return len(self.hashes.get(key, {}))

    def xadd(self, key: str, fields: dict[str, str]) -> str:
        self.streams.setdefault(key, []).append(fields)
        return f"{len(self.streams[key])}-0"

    def zadd(self, key: str, mapping: dict[str, float]) -> int:
        self.sorted_sets.setdefault(key, {}).update(mapping)
        return len(mapping)

    def zrem(self, key: str, value: str) -> int:
        return 1 if self.sorted_sets.get(key, {}).pop(value, None) is not None else 0

    def zcard(self, key: str) -> int:
        return len(self.sorted_sets.get(key, {}))

    def zscore(self, key: str, value: str) -> float | None:
        return self.sorted_sets.get(key, {}).get(value)


def make_event(delivery_id: str, **overrides: Any) -> dict[str, object]:
    event: dict[str, object] = {
        "delivery_id": delivery_id,
        "event_id": delivery_id,
        "correlation_id": f"plane:{delivery_id}",
        "event_type": "work_item.updated",
        "retry_attempt": 0,
    }
    event.update(overrides)
    return event


def test_redis_queue_enqueue_dedupes_by_delivery_id() -> None:
    redis = FakeRedis()
    queue = RedisPlaneWebhookQueue(redis, prefix="test:plane")

    first = queue.enqueue(make_event("delivery-1"))
    duplicate = queue.enqueue(make_event("delivery-1"))

    assert first.queued is True
    assert first.duplicate is False
    assert duplicate.queued is False
    assert duplicate.duplicate is True
    assert len(redis.streams["test:plane:stream"]) == 1
    assert json.loads(redis.hashes["test:plane:events"]["delivery-1"])["event_id"] == "delivery-1"


def test_redis_queue_pending_skips_dispatched_retry_and_dead_lettered() -> None:
    redis = FakeRedis()
    queue = RedisPlaneWebhookQueue(redis, prefix="test:plane")
    for delivery_id in ("delivery-pending", "delivery-dispatched", "delivery-retry", "delivery-dead"):
        queue.enqueue(make_event(delivery_id))

    queue.mark_dispatched("delivery-dispatched")
    queue.mark_failed(
        "delivery-retry",
        PlaneWebhookFailure(
            category="retryable",
            message="n8n unavailable",
            retry_after=datetime.now(timezone.utc) + timedelta(minutes=5),
        ),
    )
    queue.mark_failed(
        "delivery-dead",
        PlaneWebhookFailure(category="permanent", message="invalid event"),
    )

    assert [event["delivery_id"] for event in queue.pending_events(limit=10)] == ["delivery-pending"]


def test_redis_queue_status_reports_pending_dispatched_retry_and_dead_letter_counts() -> None:
    redis = FakeRedis()
    queue = RedisPlaneWebhookQueue(redis, prefix="test:plane")
    for delivery_id in ("delivery-pending", "delivery-dispatched", "delivery-retry", "delivery-dead"):
        queue.enqueue(make_event(delivery_id))

    queue.mark_dispatched("delivery-dispatched")
    queue.mark_failed(
        "delivery-retry",
        PlaneWebhookFailure(
            category="retryable",
            message="n8n unavailable",
            retry_after=datetime.now(timezone.utc) + timedelta(minutes=5),
        ),
    )
    queue.mark_failed(
        "delivery-dead",
        PlaneWebhookFailure(category="permanent", message="invalid event"),
    )

    status = queue.status()

    assert status.queued_count == 4
    assert status.pending_count == 1
    assert status.dispatched_count == 1
    assert status.retry_count == 1
    assert status.dead_letter_count == 1
    assert status.last_dead_letter_delivery_id == "delivery-dead"
