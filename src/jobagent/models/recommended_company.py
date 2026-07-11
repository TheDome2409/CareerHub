from pydantic import BaseModel, Field


class RecommendedCompany(BaseModel):
    company_id: int | None = None
    name: str
    website_url: str | None = None
    career_url: str | None = None
    industry: str | None = None
    region: str | None = None
    priority: int = 3
    reason: str
    recommended_by: str = "seed"
    tags: list[str] = Field(default_factory=list)
    tracking_enabled: bool = True
