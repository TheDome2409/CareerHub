from pydantic import BaseModel, Field


class JobIntelligence(BaseModel):
    extracted_skills: list[str] = Field(default_factory=list)
    extracted_competencies: list[str] = Field(default_factory=list)
    qualification_requirements: list[str] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    extraction_version: str = "job_intelligence_v1"
