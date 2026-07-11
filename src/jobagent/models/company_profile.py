from pydantic import BaseModel, Field


class CompanyProfile(BaseModel):
    id: int | None = None
    company_id: int
    mission: str | None = None
    vision: str | None = None
    culture_summary: str | None = None
    technology_summary: str | None = None
    domains: list[str] = Field(default_factory=list)
    work_models: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    kritis_relevance: bool = False
    innovation_score: int | None = None
    source_summary: str | None = None
    created_at: str
