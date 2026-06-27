from pydantic import BaseModel


class MediaItem(BaseModel):
    id: str
    type: str
    title: str
    year: int | None = None
    overview: str | None = None
    available: bool
    request_status: str | None = None


class MediaSearchResponse(BaseModel):
    items: list[MediaItem]
