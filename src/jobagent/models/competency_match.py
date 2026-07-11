from pydantic import BaseModel, Field


class CompetencyMatch(BaseModel):
    competency_name: str
    match_ratio: float = 0.0
    evidence_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
