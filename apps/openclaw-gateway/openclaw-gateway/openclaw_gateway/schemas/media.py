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
