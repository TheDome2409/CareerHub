from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class GlobalSkillCandidate(BaseModel):
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    candidate_domains: list[str] = Field(default_factory=list)
    confidence_avg: float = 0.0
    weight_avg: float = 0.0
    seen_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    source_types: list[str] = Field(default_factory=list)
    example_reasons: list[str] = Field(default_factory=list)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    status: str = "observed"
