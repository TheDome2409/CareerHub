from typing import Any

from pydantic import BaseModel, Field


class DocumentBlock(BaseModel):
    kind: str
    title: str | None = None
    content: str | dict | None = None
    items: list[Any] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentSection(BaseModel):
    title: str
    kind: str
    blocks: list[DocumentBlock] = Field(default_factory=list)
    page_break_before: bool = False
    keep_together: bool = False


class Document(BaseModel):
    title: str
    subtitle: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    sections: list[DocumentSection] = Field(default_factory=list)
