from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


OutcomeEventType = Literal[
    "viewed",
    "saved",
    "applied",
    "interview",
    "offer",
    "accepted",
    "rejected",
]


class RecommendationOutcome(BaseModel):
    outcome_id: str = Field(
        default_factory=lambda: str(uuid4())
    )
    recommendation_id: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    event_type: OutcomeEventType
    note: Optional[str] = None
