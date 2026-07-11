from pydantic import BaseModel, Field


class CompanyAnalysisSummary(BaseModel):
    company_id: int
    documents_processed: int = 0
    documents_skipped: int = 0
    evidence_created: int = 0
    evidence_updated: int = 0
    evidence_unchanged: int = 0
    processing_time_ms: int = 0
    errors: list[str] = Field(default_factory=list)

    def message(self) -> str:
        return (
            f"{self.documents_processed} Dokument(e) analysiert, "
            f"{self.evidence_created + self.evidence_updated + self.evidence_unchanged} "
            "Evidence erkannt, "
            f"{self.evidence_created} neu, "
            f"{self.evidence_updated} aktualisiert, "
            f"{self.evidence_unchanged} unverändert, "
            f"{len(self.errors)} Fehler."
        )
