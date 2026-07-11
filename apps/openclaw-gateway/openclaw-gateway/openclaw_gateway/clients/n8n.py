import httpx

from openclaw_gateway.schemas.automation import N8nSmokeResponse, RatingPromptForwardResponse
from openclaw_gateway.schemas.media import JellyfinWatchCompletedEvent


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

    async def forward_plane_webhook_event(self, event: dict[str, object]) -> dict[str, object]:
        payload = {
            "source": "plane",
            "event": event.get("event"),
            "action": event.get("action"),
            "correlation_id": event.get("correlation_id"),
            "delivery_id": event.get("delivery_id"),
            "resource_id": event.get("resource_id"),
            "webhook_id": event.get("webhook_id"),
            "actor_id": event.get("actor_id"),
        }
        for field_name in (
            "project_id",
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
            response.raise_for_status()

        return response.json()
