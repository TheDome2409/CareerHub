from pydantic import BaseModel


class CompanyConceptCandidate(BaseModel):
    raw_value: str
    canonical_value: str
    concept_type: str
    confidence: float = 0.5
    source_evidence_id: int | None = None
    source_document_id: int | None = None
    source_type: str = ""
    reason: str = ""
    status: str = "pending"
