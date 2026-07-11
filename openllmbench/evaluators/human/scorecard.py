from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from openllmbench.core.models import utc_now_iso


@dataclass(frozen=True)
class CriterionScore:
    criterion_id: str
    label: str
    score: int | None = None
    comment: str | None = None


@dataclass
class Scorecard:
    review_id: str
    run_id: str
    model: str
    task: str
    reviewer: str
    created_at: str
    version: str
    criteria: list[CriterionScore] = field(default_factory=list)
    overall_score: float | None = None
    comment: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def calculate_overall_score(self) -> float | None:
        scores = [item.score for item in self.criteria if item.score is not None]
        if not scores:
            self.overall_score = None
            return None
        self.overall_score = round(sum(scores) / len(scores), 2)
        return self.overall_score

    def to_dict(self) -> dict[str, Any]:
        self.calculate_overall_score()
        payload = asdict(self)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scorecard":
        criteria = [
            CriterionScore(
                criterion_id=str(item.get("criterion_id", "")),
                label=str(item.get("label", "")),
                score=item.get("score"),
                comment=item.get("comment"),
            )
            for item in data.get("criteria", []) or []
        ]
        return cls(
            review_id=str(data.get("review_id", "")),
            run_id=str(data.get("run_id", "")),
            model=str(data.get("model", "")),
            task=str(data.get("task", "")),
            reviewer=str(data.get("reviewer", "")),
            created_at=str(data.get("created_at", utc_now_iso())),
            version=str(data.get("version", "1.0")),
            criteria=criteria,
            overall_score=data.get("overall_score"),
            comment=data.get("comment"),
            metadata=dict(data.get("metadata", {}) or {}),
        )


def create_scorecard_from_rubric(
    *,
    rubric,
    run_id: str,
    model: str,
    task: str,
    reviewer: str,
    comment: str | None = None,
) -> Scorecard:
    scorecard = Scorecard(
        review_id=str(uuid4()),
        run_id=run_id,
        model=model,
        task=task,
        reviewer=reviewer,
        created_at=utc_now_iso(),
        version=rubric.version,
        criteria=[
            CriterionScore(
                criterion_id=criterion.id,
                label=criterion.label,
            )
            for criterion in rubric.criteria
        ],
        comment=comment,
        metadata={"rubric_id": rubric.id, "rubric_title": rubric.title},
    )
    scorecard.calculate_overall_score()
    return scorecard

