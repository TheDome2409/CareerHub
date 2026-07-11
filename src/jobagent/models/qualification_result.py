from pydantic import BaseModel, Field
from typing import Literal

from jobagent.models.qualification_requirement import (
    QualificationRequirement,
)

QualificationStatus = Literal[
    "ok",
    "needs_review",
    "formal_review",
]


class QualificationResult(BaseModel):
    eligible: bool = True
    qualification_status: QualificationStatus = "ok"
    warnings: list[str] = Field(default_factory=list)
    missing_requirements: list[QualificationRequirement] = Field(
        default_factory=list
    )
    qualification_score: int = 100
