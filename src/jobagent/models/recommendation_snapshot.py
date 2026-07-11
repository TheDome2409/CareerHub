from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class ScoreComponents(BaseModel):
    role_score: int = 0
    work_model_score: int = 0
    salary_score: int = 0
    career_score: int = 0
    employer_score: int = 0
    skill_score: int = 0
    competency_score: int = 0
    role_mismatch_penalty: int = 0


class RecommendationSnapshot(BaseModel):
    recommendation_id: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    profile_fingerprint: str
    job_id: str
    job_title: str
    company: Optional[str] = None
    query_source: Optional[str] = None
    total_score: int
    score_components: ScoreComponents
    skill_match_ratio: float = 0.0
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    salary_info: Optional[dict[str, Any]] = None
    work_model: Optional[str] = None
    qualification_status: Optional[str] = None
