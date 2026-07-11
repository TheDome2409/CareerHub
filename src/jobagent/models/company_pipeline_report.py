from pydantic import BaseModel, Field

from jobagent.models.document_processing_result import DocumentProcessingResult


class CompanyPipelineReport(BaseModel):
    company_id: int
    sources: list[dict] = Field(default_factory=list)
    documents: list[dict] = Field(default_factory=list)
    document_sizes: dict[int, int] = Field(default_factory=dict)
    processing_results: dict[int, DocumentProcessingResult] = Field(default_factory=dict)
    clean_text_lengths: dict[int, int] = Field(default_factory=dict)
    evidence_count: int = 0
    evidence_by_type: dict[str, int] = Field(default_factory=dict)
    concept_candidates: list[dict] = Field(default_factory=list)
    canonical_concepts: list[str] = Field(default_factory=list)
    unknown_concepts: list[str] = Field(default_factory=list)
    concept_types: dict[str, int] = Field(default_factory=dict)
    knowledge_draft_exists: bool = False
    knowledge_confidence: float | None = None
    review_method: str | None = None
    review_model: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
