from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _created_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class CompanyProfileMatch(BaseModel):
    company_id: int
    profile_fingerprint: str = "default"
    total_score: int = 0
    mission_score: int = 0
    domain_score: int = 0
    technology_score: int = 0
    work_model_score: int = 0
    kritis_score: int = 0
    exclusion_score: int = 0
    matched_concepts: list[str] = Field(default_factory=list)
    missing_profile_preferences: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    created_at: str = Field(default_factory=_created_at)
