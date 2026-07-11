from pathlib import Path

from jobagent.models.recommendation_outcome import (
    OutcomeEventType,
    RecommendationOutcome,
)
from jobagent.repositories import JsonRecommendationOutcomeRepository


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RECOMMENDATION_OUTCOMES_FILE = (
    PROJECT_ROOT / "data" / "recommendation_outcomes.json"
)


def _repository(
    path: str | Path = RECOMMENDATION_OUTCOMES_FILE,
) -> JsonRecommendationOutcomeRepository:
    return JsonRecommendationOutcomeRepository(
        path
    )


def create_outcome(
    recommendation_id: str,
    event_type: OutcomeEventType,
    note: str | None = None,
) -> RecommendationOutcome:
    return RecommendationOutcome(
        recommendation_id=recommendation_id,
        event_type=event_type,
        note=note,
    )


def load_outcomes(
    path: str | Path = RECOMMENDATION_OUTCOMES_FILE,
) -> list[RecommendationOutcome]:
    return _repository(
        path
    ).load_outcomes()


def save_outcomes(
    outcomes: list[RecommendationOutcome],
    path: str | Path = RECOMMENDATION_OUTCOMES_FILE,
) -> None:
    _repository(
        path
    ).save_outcomes(
        outcomes
    )


def append_outcome(
    outcome: RecommendationOutcome,
    path: str | Path = RECOMMENDATION_OUTCOMES_FILE,
) -> list[RecommendationOutcome]:
    return _repository(
        path
    ).append_outcome(
        outcome
    )


def get_outcomes_for_recommendation(
    recommendation_id: str,
    outcomes: list[RecommendationOutcome] | None = None,
    path: str | Path = RECOMMENDATION_OUTCOMES_FILE,
) -> list[RecommendationOutcome]:
    if outcomes is None:
        return _repository(
            path
        ).get_outcomes_for_recommendation(
            recommendation_id
        )

    return [
        outcome
        for outcome in outcomes
        if outcome.recommendation_id == recommendation_id
    ]
