import logging
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from openclaw_gateway.auth import require_gateway_token
from openclaw_gateway.clients.n8n import N8nClient
from openclaw_gateway.schemas.automation import N8nSmokeGatewayRequest, N8nSmokeGatewayResponse
from openclaw_gateway.settings import GatewaySettings


logger = logging.getLogger(__name__)


def build_automation_router(settings: GatewaySettings) -> APIRouter:
    router = APIRouter(
        prefix="/v1/automation",
        dependencies=[Depends(require_gateway_token(settings))],
    )

    def n8n_client() -> N8nClient:
        return N8nClient(
            base_url=str(settings.n8n_webhook_base_url),
            smoke_path=settings.n8n_openclaw_smoke_path,
            rating_prompt_path=settings.n8n_jellyfin_rating_prompt_path,
            timeout_seconds=settings.upstream_timeout_seconds,
        )

    @router.post("/n8n/openclaw-smoke")
    async def n8n_openclaw_smoke(
        smoke_request: N8nSmokeGatewayRequest | None = None,
    ) -> N8nSmokeGatewayResponse:
        request_id = smoke_request.request_id if smoke_request and smoke_request.request_id else uuid4().hex
        try:
            result = await n8n_client().openclaw_smoke(request_id=request_id)
        except httpx.TimeoutException as exc:
            logger.warning("n8n smoke timed out", extra={"request_id": request_id})
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="n8n timed out",
            ) from exc
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "n8n smoke returned upstream error",
                extra={"request_id": request_id, "upstream_status": exc.response.status_code},
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"n8n returned {exc.response.status_code}",
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("n8n smoke request failed", extra={"request_id": request_id})
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="n8n request failed",
            ) from exc

        logger.info("n8n smoke succeeded", extra={"request_id": request_id})
        return N8nSmokeGatewayResponse(
            ok=result.ok,
            workflow=result.workflow,
            received=result.received,
            request_id=request_id,
        )

    return router
