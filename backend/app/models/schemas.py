from pydantic import BaseModel, Field


class TorrentResult(BaseModel):
    title: str
    infohash: str
    magnet: str | None = None
    source: str
    seeders: int = 0
    leechers: int = 0
    size_bytes: int | None = None
    size_label: str | None = None
    resolution: str | None = None
    category: str | None = None
    uploaded_at: str | None = None
    imdb_rating: float | None = None


class Metadata(BaseModel):
    title: str | None = None
    year: str | None = None
    synopsis: str | None = None
    poster_url: str | None = None
    rating: float | None = None
    genres: list[str] = Field(default_factory=list)


class SearchResultItem(BaseModel):
    title: str
    source: str
    infohash: str
    magnet: str | None = None
    seeders: int = 0
    leechers: int = 0
    size_label: str | None = None
    resolution: str | None = None
    category: str | None = None
    uploaded_at: str | None = None
    instant_available: bool = True
    metadata: Metadata = Field(default_factory=Metadata)


class SearchResponse(BaseModel):
    query: str
    total_found: int
    total_instant: int
    items: list[SearchResultItem]
    warning: str | None = None


class ResolveRequest(BaseModel):
    magnet: str


class ResolveResponse(BaseModel):
    success: bool
    stream_url: str | None = None
    download_url: str | None = None
    filename: str | None = None
    message: str | None = None
