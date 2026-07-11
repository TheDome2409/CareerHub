from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from jobagent.models.job import CompanyIntel, Job


CompanyGroundTruthTopic = Literal[
    "culture",
    "leadership",
    "innovation",
    "digitalization",
    "work_life_balance",
    "process_quality",
    "technology",
    "career",
    "stability",
    "sustainability",
    "employer_branding",
    "other",
]

CompanyGroundTruthUserAssessment = Literal[
    "stimmt",
    "teilweise",
    "falsch",
    "unbekannt",
]


def _created_at() -> str:
    return datetime.now(
        timezone.utc
    ).replace(
        microsecond=0
    ).isoformat()


class Company(BaseModel):
    id: int | None = None
    name: str
    normalized_name: str
    website_url: str | None = None
    career_url: str | None = None
    industry: str | None = None
    status: str = "active"
    ground_truth_available: bool = False
    relationship_status: str | None = None
    created_at: str
    updated_at: str


class CompanyProfile(BaseModel):
    name: str
    description: str = ""
    source_type: str | None = None
    source_name: str | None = None
    jobs: list[Job] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    work_models: list[str] = Field(default_factory=list)
    focus_areas: list[str] = Field(default_factory=list)
    possible_use_cases: list[str] = Field(default_factory=list)
    detected_skills: list[str] = Field(default_factory=list)
    detected_competencies: list[str] = Field(default_factory=list)
    qualification_requirements: list[str] = Field(default_factory=list)
    company_intel: CompanyIntel = Field(default_factory=CompanyIntel)
    ground_truth_available: bool = False
    relationship_status: str | None = None


class CompanyGroundTruthReview(BaseModel):
    company_id: int | str
    topic: CompanyGroundTruthTopic
    claim: str
    system_assessment: str
    user_assessment: CompanyGroundTruthUserAssessment
    user_comment: str = ""
    confidence: float = 0.0
    created_at: str = Field(default_factory=_created_at)
