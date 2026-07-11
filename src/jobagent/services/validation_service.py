from jobagent.models.validation_summary import ValidationSummary


OUTCOME_EVENT_TYPES = (
    "viewed",
    "saved",
    "applied",
    "interview",
    "offer",
    "accepted",
    "rejected",
)


def _get_value(item, name: str, default=None):
    if isinstance(item, dict):
        return item.get(name, default)

    return getattr(item, name, default)


def _recommendation_id(item) -> str:
    return str(
        _get_value(item, "recommendation_id", "") or ""
    )


def get_recommendation_outcomes(
    recommendation_id: str,
    outcomes,
) -> list:
    return [
        outcome
        for outcome in outcomes
        if _recommendation_id(outcome) == recommendation_id
    ]


def _event_types_for_recommendation(
    recommendation_id: str,
    outcomes,
) -> set[str]:
    return {
        str(_get_value(outcome, "event_type", "") or "")
        for outcome in get_recommendation_outcomes(
            recommendation_id,
            outcomes,
        )
    }


def calculate_conversion_rates(
    total_recommendations: int,
    applied_count: int,
    interview_count: int,
    offer_count: int,
    accepted_count: int,
) -> dict[str, float]:
    if total_recommendations <= 0:
        return {
            "application_rate": 0.0,
            "interview_rate": 0.0,
            "offer_rate": 0.0,
            "acceptance_rate": 0.0,
        }

    return {
        "application_rate": round(
            applied_count / total_recommendations * 100,
            1,
        ),
        "interview_rate": round(
            interview_count / total_recommendations * 100,
            1,
        ),
        "offer_rate": round(
            offer_count / total_recommendations * 100,
            1,
        ),
        "acceptance_rate": round(
            accepted_count / total_recommendations * 100,
            1,
        ),
    }


def build_validation_summary(
    snapshots,
    outcomes,
) -> ValidationSummary:
    recommendation_ids = [
        _recommendation_id(snapshot)
        for snapshot in snapshots
        if _recommendation_id(snapshot)
    ]
    unique_recommendation_ids = list(
        dict.fromkeys(recommendation_ids)
    )
    event_counts = {
        event_type: 0
        for event_type in OUTCOME_EVENT_TYPES
    }

    for recommendation_id in unique_recommendation_ids:
        event_types = _event_types_for_recommendation(
            recommendation_id,
            outcomes,
        )

        for event_type in OUTCOME_EVENT_TYPES:
            if event_type in event_types:
                event_counts[event_type] += 1

    rates = calculate_conversion_rates(
        total_recommendations=len(unique_recommendation_ids),
        applied_count=event_counts["applied"],
        interview_count=event_counts["interview"],
        offer_count=event_counts["offer"],
        accepted_count=event_counts["accepted"],
    )

    return ValidationSummary(
        total_recommendations=len(unique_recommendation_ids),
        viewed_count=event_counts["viewed"],
        saved_count=event_counts["saved"],
        applied_count=event_counts["applied"],
        interview_count=event_counts["interview"],
        offer_count=event_counts["offer"],
        accepted_count=event_counts["accepted"],
        rejected_count=event_counts["rejected"],
        **rates,
    )
