from pydantic import BaseModel
from typing import List


class ScoreResult(BaseModel):
    total_score: int

    reasons: List[str] = []