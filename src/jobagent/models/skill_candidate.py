from dataclasses import dataclass
from typing import Optional


@dataclass
class SkillCandidate:
    name: str
    category: str
    confidence: float = 1.0
    weight: int = 5
    enabled: bool = True
    source: str = ""
    provider: str = "keyword"
    candidate_domain: Optional[str] = None
