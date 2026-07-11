from typing import Literal

from pydantic import BaseModel


RequirementType = Literal[
    "education",
    "certification",
    "experience",
    "leadership",
    "license",
    "security_clearance",
    "driving_license",
]

RequirementSeverity = Literal[
    "warning",
    "review",
    "blocking",
]


class QualificationRequirement(BaseModel):
    role_pattern: str
    requirement_type: RequirementType
    description: str
    severity: RequirementSeverity = "review"
