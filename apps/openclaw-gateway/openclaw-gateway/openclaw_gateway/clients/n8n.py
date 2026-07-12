from dataclasses import dataclass
from typing import Literal

import httpx

from openclaw_gateway.schemas.automation import N8nSmokeResponse, RatingPromptForwardResponse
from openclaw_gateway.schemas.media import JellyfinWatchCompletedEvent


@dataclass(frozen=True)
class PlaneDispatchResult:
    ok: bool
    failure_type: Literal["retryable", "permanent"] | None = None
    error_code: str | None = None
    detail: str | None = None


class N8nClient:
    def __init__(
        self,
        base_url: str,
        smoke_path: str,
        rating_prompt_path: str,
        plane_dispatch_path: str,
        timeout_seconds: float,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._smoke_path = smoke_path
        self._rating_prompt_path = rating_prompt_path
        self._plane_dispatch_path = plane_dispatch_path
        self._timeout = httpx.Timeout(timeout_seconds)

    async def openclaw_smoke(self, request_id: str) -> N8nSmokeResponse:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}{self._smoke_path}",
                json={"source": "openclaw", "test": True, "request_id": request_id},
            )
            response.raise_for_status()

        return N8nSmokeResponse.model_validate(response.json())

    async def forward_rating_prompt(
        self, event: JellyfinWatchCompletedEvent
    ) -> RatingPromptForwardResponse:
        payload = {
            "source": "jellyfin",
            "event": "watch_completed",
            "item_id": event.item_id,
            "title": event.title,
            "year": event.year,
            "watched_at": event.watched_at,
            "user_id": event.user_id,
            "dedupe_key": event.dedupe_key,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(f"{self._base_url}{self._rating_prompt_path}", json=payload)
            response.raise_for_status()

        return RatingPromptForwardResponse.model_validate(response.json())

    async def forward_plane_webhook_event(self, event: dict[str, object]) -> PlaneDispatchResult:
        payload = {
            "schema_version": event.get("schema_version"),
            "event_id": event.get("event_id") or event.get("delivery_id"),
            "event_type": event.get("event_type"),
            "idempotency_key": event.get("idempotency_key") or event.get("event_id") or event.get("delivery_id"),
            "correlation_id": event.get("correlation_id"),
            "causation_id": event.get("causation_id"),
            "origin": event.get("origin", "plane"),
            "retry_attempt": event.get("retry_attempt", 0),
            "raw_payload_hash": event.get("raw_payload_hash"),
            "source": "plane",
            "event": event.get("event"),
            "action": event.get("action"),
            "delivery_id": event.get("delivery_id"),
            "resource_id": event.get("resource_id"),
            "webhook_id": event.get("webhook_id"),
            "actor_id": event.get("actor_id"),
        }
        for field_name in (
            "team",
            "project_id",
            "source_identifier",
            "sequence_id",
            "name",
            "state_id",
            "state_name",
            "priority",
            "label_names",
        ):
            if field_name in event:
                payload[field_name] = event.get(field_name)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(f"{self._base_url}{self._plane_dispatch_path}", json=payload)
        if response.status_code >= 500:
            return PlaneDispatchResult(
                ok=False,
                failure_type="retryable",
                error_code=f"http_{response.status_code}",
                detail="n8n returned a retryable error",
            )
        if response.status_code >= 400:
            return PlaneDispatchResult(
                ok=False,
                failure_type="permanent",
                error_code=f"http_{response.status_code}",
                detail="n8n returned a permanent dispatch error",
            )
        try:
            body = response.json()
        except ValueError:
            return PlaneDispatchResult(
                ok=False,
                failure_type="retryable",
                error_code="invalid_n8n_response",
                detail="n8n returned invalid json",
            )
        if not isinstance(body, dict):
            return PlaneDispatchResult(
                ok=False,
                failure_type="retryable",
                error_code="invalid_n8n_response",
                detail="n8n returned invalid json",
            )
        if body.get("ok") is False:
            failure_type = body.get("failure_type")
            return PlaneDispatchResult(
                ok=False,
                failure_type=failure_type if failure_type in {"retryable", "permanent"} else "retryable",
                error_code=body.get("error_code") if isinstance(body.get("error_code"), str) else None,
                detail=body.get("detail") if isinstance(body.get("detail"), str) else None,
            )
        return PlaneDispatchResult(ok=True)
