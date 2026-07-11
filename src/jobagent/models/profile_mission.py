from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _created_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ProfileMission(BaseModel):
    summary: str = ""
    mission_keywords: list[str] = Field(default_factory=list)
    interest_domains: list[str] = Field(default_factory=list)
    preferred_problem_domains: list[str] = Field(default_factory=list)
    preferred_technologies: list[str] = Field(default_factory=list)
    preferred_work_models: list[str] = Field(default_factory=list)
    preferred_company_types: list[str] = Field(default_factory=list)
    kritis_affinity: float = 0.0
    innovation_affinity: float = 0.0
    public_sector_affinity: float = 0.0
    research_affinity: float = 0.0
    confidence: float = 0.0
    created_at: str = Field(default_factory=_created_at)
