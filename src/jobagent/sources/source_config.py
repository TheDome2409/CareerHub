from pydantic import BaseModel


class SourceConfig(BaseModel):
    type: str
    enabled: bool = True

    path: str | None = None
    url: str | None = None

    query: str | None = None
    category: str | None = None
    location: str | None = None
    radius_km: int | None = None

    max_results: int | None = None
    published_since_days: int | None = None

    default_company: str | None = None
    default_work_model: str | None = None


class SourcesConfig(BaseModel):
    sources: list[SourceConfig]
