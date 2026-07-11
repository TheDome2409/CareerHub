from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    MISSION = "mission"
    VISION = "vision"
    PURPOSE = "purpose"
    BENEFIT = "benefit"
    CULTURE = "culture"
    TECHNOLOGY = "technology"
    BUSINESS_UNIT = "business_unit"
    PRODUCT = "product"
    SERVICE = "service"
    LOCATION = "location"
    INNOVATION = "innovation"
    CAREER = "career"
    TRAVEL = "travel"
    LANGUAGE = "language"
    SALARY = "salary"
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    MANAGEMENT = "management"
    SUSTAINABILITY = "sustainability"
    KRITIS = "kritis"
    OTHER = "other"


def _created_at() -> str:
    return datetime.now(
        timezone.utc
    ).replace(
        microsecond=0
    ).isoformat()


class CompanyEvidence(BaseModel):
    id: int | None = None
    company_id: int
    document_id: int | None = None
    evidence_type: EvidenceType | str
    title: str | None = None
    text: str
    source_type: str
    source_name: str
    source_url: str
    section: str | None = None
    confidence: float | None = None
    language: str | None = None
    created_at: str = Field(default_factory=_created_at)
