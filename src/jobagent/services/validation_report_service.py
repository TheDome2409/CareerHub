from pathlib import Path

from jobagent.services.recommendation_outcome_service import (
    load_outcomes,
)
from jobagent.services.recommendation_snapshot_service import (
    load_snapshots,
)
from jobagent.services.validation_service import (
    build_validation_summary,
    get_recommendation_outcomes,
)


TOP_OUTCOME_PRIORITY = (
    "accepted",
    "offer",
    "interview",
    "applied",
    "saved",
    "viewed",
)
IGNORED_RECOMMENDATION_LIMIT = 10


def _get_value(item, name: str, default=None):
    if isinstance(item, dict):
        return item.get(name, default)

    return getattr(item, name, default)


def _recommendation_id(snapshot) -> str:
    return str(
        _get_value(snapshot, "recommendation_id", "") or ""
    )


def _recommendation_ids(items) -> set[str]:
    return {
        _recommendation_id(item)
        for item in items
        if _recommendation_id(item)
    }


def _snapshot_ids(snapshots) -> set[str]:
    return _recommendation_ids(
        snapshots
    )


def _outcome_ids(outcomes) -> set[str]:
    return _recommendation_ids(
        outcomes
    )


def _linked_ids(snapshots, outcomes) -> set[str]:
    return _snapshot_ids(
        snapshots
    ).intersection(
        _outcome_ids(outcomes)
    )


def _snapshot_ids_without_outcome(snapshots, outcomes) -> set[str]:
    return _snapshot_ids(
        snapshots
    ).difference(
        _outcome_ids(outcomes)
    )


def _outcome_ids_without_snapshot(snapshots, outcomes) -> set[str]:
    return _outcome_ids(
        outcomes
    ).difference(
        _snapshot_ids(snapshots)
    )


def _job_title(snapshot) -> str:
    return str(
        _get_value(snapshot, "job_title", "") or "Unbekannter Job"
    )


def _score(snapshot) -> int:
    return int(
        _get_value(snapshot, "total_score", 0) or 0
    )


def _qualification_status(snapshot) -> str | None:
    for key in [
        "qualification_status",
        "qualification_state",
        "qualification",
    ]:
        value = _get_value(snapshot, key)

        if value:
            return str(value)

    return None


def _event_types(outcomes) -> list[str]:
    return [
        str(_get_value(outcome, "event_type", "") or "")
        for outcome in outcomes
        if _get_value(outcome, "event_type")
    ]


def _best_outcome(event_types: list[str]) -> str | None:
    event_type_set = set(event_types)

    for event_type in TOP_OUTCOME_PRIORITY:
        if event_type in event_type_set:
            return event_type

    return None


def _format_rate(value: float) -> str:
    return f"{value:.1f}%"


def _report_header() -> list[str]:
    return [
        "================================",
        "CAREERHUB VALIDATION REPORT",
        "================================",
        "",
    ]


def _summary_lines(summary, snapshots, outcomes) -> list[str]:
    linked_count = len(_linked_ids(snapshots, outcomes))
    linked_line = (
        "Linked Recommendations: all (1)"
        if summary.total_recommendations == 1 and linked_count == 1
        else f"Linked Recommendations: {linked_count}"
    )

    return [
        f"Recommendations: {summary.total_recommendations}",
        linked_line,
        (
            "Snapshots without Outcome: "
            f"{len(_snapshot_ids_without_outcome(snapshots, outcomes))}"
        ),
        (
            "Outcomes without Snapshot: "
            f"{len(_outcome_ids_without_snapshot(snapshots, outcomes))}"
        ),
        "",
        f"Viewed: {summary.viewed_count}",
        f"Saved: {summary.saved_count}",
        f"Applied: {summary.applied_count}",
        f"Interview: {summary.interview_count}",
        f"Offer: {summary.offer_count}",
        f"Accepted: {summary.accepted_count}",
        f"Rejected: {summary.rejected_count}",
        "",
        f"Application Rate: {_format_rate(summary.application_rate)}",
        f"Interview Rate: {_format_rate(summary.interview_rate)}",
        f"Offer Rate: {_format_rate(summary.offer_rate)}",
        f"Acceptance Rate: {_format_rate(summary.acceptance_rate)}",
        "",
    ]


def _top_outcome_lines(snapshots, outcomes) -> list[str]:
    lines = [
        "================================",
        "TOP OUTCOMES",
        "================================",
    ]
    found = False

    for snapshot in snapshots:
        recommendation_id = _recommendation_id(snapshot)
        snapshot_outcomes = get_recommendation_outcomes(
            recommendation_id,
            outcomes,
        )
        outcome = _best_outcome(
            _event_types(snapshot_outcomes)
        )

        if not outcome:
            continue

        found = True
        lines.append("")
        lines.append(f"Outcome: {outcome}")
        lines.append(f"Score: {_score(snapshot)}")
        lines.append(f"Job: {_job_title(snapshot)}")

        qualification_status = _qualification_status(snapshot)

        if qualification_status:
            lines.append(f"Qualification: {qualification_status}")

    if not found:
        lines.append("")
        lines.append("Keine verknuepften Outcomes vorhanden.")

    lines.append("")

    return lines


def _orphan_outcome_lines(snapshots, outcomes) -> list[str]:
    lines = [
        "================================",
        "OUTCOMES WITHOUT SNAPSHOT",
        "================================",
    ]
    orphan_ids = _outcome_ids_without_snapshot(
        snapshots,
        outcomes,
    )

    if not orphan_ids:
        lines.append("")
        lines.append("Keine Outcomes ohne Snapshot vorhanden.")
        lines.append("")
        return lines

    for recommendation_id in sorted(orphan_ids):
        event_types = _event_types(
            get_recommendation_outcomes(
                recommendation_id,
                outcomes,
            )
        )
        lines.append("")
        lines.append(f"Recommendation ID: {recommendation_id}")
        lines.append(
            "Outcomes: "
            + (
                ", ".join(event_types)
                if event_types
                else "none"
            )
        )

    lines.append("")

    return lines


def _ignored_recommendation_lines(snapshots, outcomes) -> list[str]:
    lines = [
        "================================",
        "IGNORED RECOMMENDATIONS",
        "================================",
    ]
    found = False

    ignored_count = 0

    for snapshot in snapshots:
        recommendation_id = _recommendation_id(snapshot)
        snapshot_outcomes = get_recommendation_outcomes(
            recommendation_id,
            outcomes,
        )

        if snapshot_outcomes:
            continue

        found = True
        ignored_count += 1

        if ignored_count > IGNORED_RECOMMENDATION_LIMIT:
            continue

        lines.append("")
        lines.append(f"Score: {_score(snapshot)}")
        lines.append(f"Job: {_job_title(snapshot)}")
        lines.append("Outcome: none")

    if ignored_count > IGNORED_RECOMMENDATION_LIMIT:
        hidden_count = ignored_count - IGNORED_RECOMMENDATION_LIMIT
        lines.append("")
        lines.append(
            f"... weitere {hidden_count} ignorierte Empfehlungen ausgeblendet."
        )

    if not found:
        lines.append("")
        lines.append("Keine ignorierten Empfehlungen vorhanden.")

    lines.append("")

    return lines


def generate_validation_report(
    snapshot_path: str | Path | None = None,
    outcome_path: str | Path | None = None,
) -> str:
    snapshots = (
        load_snapshots(snapshot_path)
        if snapshot_path is not None
        else load_snapshots()
    )
    outcomes = (
        load_outcomes(outcome_path)
        if outcome_path is not None
        else load_outcomes()
    )
    summary = build_validation_summary(
        snapshots,
        outcomes,
    )
    lines = []
    lines.extend(_report_header())
    lines.extend(
        _summary_lines(
            summary,
            snapshots,
            outcomes,
        )
    )
    lines.extend(_top_outcome_lines(snapshots, outcomes))
    lines.extend(_orphan_outcome_lines(snapshots, outcomes))
    lines.extend(_ignored_recommendation_lines(snapshots, outcomes))

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    print(
        generate_validation_report(),
        end="",
    )


if __name__ == "__main__":
    main()
