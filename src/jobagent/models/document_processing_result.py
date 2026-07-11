from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _created_at() -> str:
    return datetime.now(
        timezone.utc
    ).replace(
        microsecond=0
    ).isoformat()


class DocumentProcessingResult(BaseModel):
    source_type: str
    mime_type: str | None = None
    encoding: str | None = None
    original_size: int = 0
    processed_size: int = 0
    ocr_used: bool = False
    language: str | None = None
    title: str | None = None
    clean_text: str = ""
    metadata: dict = Field(default_factory=dict)
    processing_steps: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=_created_at)
