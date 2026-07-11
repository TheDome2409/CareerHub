from pydantic import BaseModel, Field


class CompanyMatchResult(BaseModel):
    id: int | None = None
    company_id: int
    profile_fingerprint: str
    mission_score: int | None = None
    culture_score: int | None = None
    technology_score: int | None = None
    work_model_score: int | None = None
    travel_score: int | None = None
    total_score: int | None = None
    reasons: list[str] = Field(default_factory=list)
    created_at: str
