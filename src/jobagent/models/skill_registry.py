from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


SkillRegistryStatus = Literal[
    "active",
    "inactive",
    "rejected",
    "conflict",
]


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).replace(
        microsecond=0
    ).isoformat()


class SkillRegistryEntry(BaseModel):
    id: int | None = None
    canonical_name: str
    display_name: str
    type: str = "skill"
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    created_by: str = "system"
    source: str = "unknown"
    status: SkillRegistryStatus = "active"


class SkillRegistryConflict(BaseModel):
    raw_name: str
    canonical_name: str
    requested_type: str
    existing_type: str
    existing_skill_id: int
    reason: str
