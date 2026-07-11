from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _created_at() -> str:
    return datetime.now(
        timezone.utc
    ).replace(
        microsecond=0
    ).isoformat()


class CompanyKnowledgeDraft(BaseModel):
    id: int | None = None
    company_id: int
    mission: str | None = None
    vision: str | None = None
    culture: str | None = None
    business_domains: list[str] = Field(default_factory=list)
    mission_keywords: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    work_models: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    innovation_areas: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    kritis_relevance: bool = False
    confidence: float = 0.0
    evidence_count: int = 0
    created_at: str = Field(default_factory=_created_at)
    source_documents: list[int] = Field(default_factory=list)
    source_evidence_ids: list[int] = Field(default_factory=list)
    canonical_concepts: list[str] = Field(default_factory=list)
    concept_statistics: dict[str, float | int] = Field(default_factory=dict)
    review_method: str = "rule_based"
    review_model: str | None = None
    review_notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(
            mode="json",
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompanyKnowledgeDraft":
        return cls.model_validate(
            data or {}
        )
