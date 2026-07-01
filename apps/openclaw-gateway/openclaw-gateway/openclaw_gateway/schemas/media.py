from typing import Annotated, Literal

from pydantic import BaseModel, Field


class MediaItem(BaseModel):
    id: str
    type: str
    title: str
    year: int | None = None
    overview: str | None = None
    available: bool
    request_status: str | None = None
    library: str | None = None
    runtime_minutes: int | None = None
    genres: list[str] = Field(default_factory=list)


class MediaPagination(BaseModel):
    mode: Literal["full_response", "window"] = "full_response"
    start_index: int = 0
    limit: int | None = None
    total: int | None = None


class MediaSearchResponse(BaseModel):
    items: list[MediaItem]
    pagination: MediaPagination = Field(default_factory=MediaPagination)


class JellyseerrRequestCreate(BaseModel):
    media_type: Literal["movie", "tv"]
    tmdb_id: Annotated[int, Field(gt=0)]
    note: str | None = None
    dry_run: bool = True


class JellyseerrRequestResponse(BaseModel):
    status: Literal["created", "duplicate", "valid"]
    media_type: Literal["movie", "tv"]
    tmdb_id: int
    message: str
    request_id: int | None = None
    duplicate: bool
    dry_run: bool


class JellyfinWatchCompletedEvent(BaseModel):
    event: str
    item_id: Annotated[str, Field(min_length=1)]
    item_type: Literal["movie"]
    title: Annotated[str, Field(min_length=1)]
    year: int | None = None
    watched_at: Annotated[str, Field(min_length=1)]
    user_id: str | None = None
    completed: Literal[True]

    @property
    def dedupe_key(self) -> str:
        return f"{self.item_id}:{self.watched_at}"


class JellyfinWatchCompletedResponse(BaseModel):
    status: Literal["forwarded"]
    dedupe_key: str
    forwarded: bool
    message: str


class JellyseerrRequestCreate(BaseModel):
    media_type: Literal["movie", "tv"]
    tmdb_id: Annotated[int, Field(gt=0)]
    note: str | None = None
    dry_run: bool = True


class JellyseerrRequestResponse(BaseModel):
    status: Literal["created", "duplicate", "valid"]
    media_type: Literal["movie", "tv"]
    tmdb_id: int
    message: str
    request_id: int | None = None
    duplicate: bool
    dry_run: bool


class JellyfinWatchCompletedEvent(BaseModel):
    event: str
    item_id: Annotated[str, Field(min_length=1)]
    item_type: Literal["movie"]
    title: Annotated[str, Field(min_length=1)]
    year: int | None = None
    watched_at: Annotated[str, Field(min_length=1)]
    user_id: str | None = None
    completed: Literal[True]

    @property
    def dedupe_key(self) -> str:
        return f"{self.item_id}:{self.watched_at}"


class JellyfinWatchCompletedResponse(BaseModel):
    status: Literal["forwarded"]
    dedupe_key: str
    forwarded: bool
    message: str


class SeriesStatistics(BaseModel):
    season_count: int | None = None
    episode_file_count: int | None = None
    episode_count: int | None = None
    total_episode_count: int | None = None
    size_on_disk: int | None = None


class SeriesSummary(BaseModel):
    id: str
    tvdb_id: int | None = None
    title: str
    year: int | None = None
    status: str | None = None
    monitored: bool
    path: str | None = None
    quality_profile_id: int | None = None
    statistics: SeriesStatistics
    tags: list[int]


class SeriesSummaryResponse(BaseModel):
    items: list[SeriesSummary]


class MovieStatistics(BaseModel):
    movie_file_count: int | None = None
    size_on_disk: int | None = None


class MovieSummary(BaseModel):
    id: str
    tmdb_id: int | None = None
    title: str
    year: int | None = None
    status: str | None = None
    monitored: bool
    has_file: bool
    available: bool
    path: str | None = None
    quality_profile_id: int | None = None
    statistics: MovieStatistics
    tags: list[int]


class MovieSummaryResponse(BaseModel):
    items: list[MovieSummary]
