from pydantic import BaseModel


class RatingPromptForwardResponse(BaseModel):
    ok: bool
    workflow: str
    received: bool
    dedupe_key: str
