from pydantic import BaseModel, Field
from typing import List


class ScoreResult(BaseModel):
    total_score: int
    reasons: List[str] = Field(default_factory=list)
    role_score: int = 0
    work_model_score: int = 0
    salary_score: int = 0
    career_score: int = 0
    employer_score: int = 0
    skill_score: int = 0
    competency_score: int = 0
    role_mismatch_penalty: int = 0
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    skill_match_ratio: float = 0.0
    competency_match_ratio: float = 0.0
