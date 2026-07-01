from pydantic import BaseModel


class N8nSmokeGatewayRequest(BaseModel):
    request_id: str | None = None


class N8nSmokeResponse(BaseModel):
    ok: bool
    workflow: str
    received: bool


class N8nSmokeGatewayResponse(N8nSmokeResponse):
    request_id: str


class RatingPromptForwardResponse(BaseModel):
    ok: bool
    workflow: str
    received: bool
    dedupe_key: str
