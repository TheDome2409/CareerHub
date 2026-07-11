from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from jobagent.models.company_enums import (
    BusinessDomain,
    WorkModel,
)


def _now() -> str:
    return datetime.now(
        timezone.utc
    ).replace(
        microsecond=0
    ).isoformat()


class CompanyKnowledge(BaseModel):
    mission: str | None = None
    vision: str | None = None
    purpose: str | None = None
    core_values: list[str] = Field(default_factory=list)
    business_domains: list[BusinessDomain | str] = Field(
        default_factory=list
    )
    technologies: list[str] = Field(default_factory=list)
    business_units: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    markets: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    work_models: list[WorkModel | str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    innovation_areas: list[str] = Field(default_factory=list)
    critical_infrastructure: bool = False
    digitalization_maturity: int | None = None
    innovation_score: int | None = None
    sustainability_score: int | None = None
    growth_signals: list[str] = Field(default_factory=list)
    source_summary: str | None = None
    culture_summary: str | None = None
    technology_summary: str | None = None
    leadership_style: str | None = None
    hiring_strategy: str | None = None
    travel_expectation: str | None = None
    language_requirements: list[str] = Field(default_factory=list)
    notes: str | None = None
    confidence: float = 0.0
    created_at: str = Field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(
            mode="json",
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompanyKnowledge":
        return cls.model_validate(
            data or {}
        )
