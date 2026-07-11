from enum import Enum

from pydantic import BaseModel


class RelationshipType(str, Enum):
    PARENT_COMPANY = "parent_company"
    SUBSIDIARY = "subsidiary"
    SISTER_COMPANY = "sister_company"
    GROUP_COMPANY = "group_company"
    SHAREHOLDER = "shareholder"
    OWNERSHIP = "ownership"
    MANAGEMENT_OVERLAP = "management_overlap"
    BRAND_OWNER = "brand_owner"
    LEGAL_SUCCESSOR = "legal_successor"
    FORMER_NAME = "former_name"
    PARTNER = "partner"
    OTHER = "other"


class RelationshipDirection(str, Enum):
    OUTGOING = "outgoing"
    INCOMING = "incoming"
    BIDIRECTIONAL = "bidirectional"
    UNKNOWN = "unknown"


class CompanyRelationship(BaseModel):
    id: int | None = None
    company_id: int
    related_company_id: int | None = None
    related_company_name: str
    relationship_type: RelationshipType | str
    direction: RelationshipDirection | str = RelationshipDirection.UNKNOWN
    confidence: float | None = None
    source: str | None = None
    source_url: str | None = None
    evidence_text: str | None = None
    active: bool = True
    observed_at: str
    created_at: str
