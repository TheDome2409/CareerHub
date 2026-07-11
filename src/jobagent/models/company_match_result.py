from pydantic import BaseModel, Field

from jobagent.models.company import CompanyProfile
from jobagent.models.job import Job


class CompanyMatchResult(BaseModel):
    company: CompanyProfile
    total_score: int = 0
    role_opportunity_score: int = 0
    skill_coverage_score: int = 0
    competency_coverage_score: int = 0
    strategic_fit_score: int = 0
    preference_score: int = 0
    risk_flags: list[str] = Field(default_factory=list)
    matching_jobs: list[Job] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    application_recommendation: str = ""
