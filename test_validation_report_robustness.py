import json
from pathlib import Path

from jobagent.models.job import Job
from jobagent.services.recommendation_outcome_service import (
    append_outcome,
    create_outcome,
)
from jobagent.services.recommendation_snapshot_service import (
    build_recommendation_snapshot,
    save_snapshot_once,
)
from jobagent.services.validation_report_service import (
    generate_validation_report,
)


def _snapshot(
    recommendation_id: str,
    title: str = "Test Job",
    score: int = 50,
):
    job = Job(
        title=title,
        company="Example GmbH",
    )

    return build_recommendation_snapshot(
        profile_fingerprint="profile-123",
        job=job,
        score_result={
            "total_score": score,
            "skill_score": 10,
            "skill_match_ratio": 0.5,
        },
        recommendation_id=recommendation_id,
        qualification_status="needs_review",
    )


def test_validation_report_empty_state(tmp_path: Path):
    report = generate_validation_report(
        tmp_path / "missing_snapshots.json",
        tmp_path / "missing_outcomes.json",
    )

    assert "Recommendations: 0" in report
    assert "Linked Recommendations: 0" in report
    assert "Snapshots without Outcome: 0" in report
    assert "Outcomes without Snapshot: 0" in report


def test_validation_report_empty_files(tmp_path: Path):
    snapshot_path = tmp_path / "snapshots.json"
    outcome_path = tmp_path / "outcomes.json"
    snapshot_path.write_text("", encoding="utf-8")
    outcome_path.write_text("", encoding="utf-8")

    report = generate_validation_report(
        snapshot_path,
        outcome_path,
    )

    assert "Recommendations: 0" in report
    assert "Keine verknuepften Outcomes vorhanden." in report


def test_validation_report_only_snapshots(tmp_path: Path):
    snapshot_path = tmp_path / "snapshots.json"
    outcome_path = tmp_path / "outcomes.json"

    save_snapshot_once(
        _snapshot("rec-1", "Ignored Job"),
        snapshot_path,
    )

    report = generate_validation_report(
        snapshot_path,
        outcome_path,
    )

    assert "Recommendations: 1" in report
    assert "Snapshots without Outcome: 1" in report
    assert "Job: Ignored Job" in report
    assert "Outcome: none" in report


def test_validation_report_only_orphan_outcomes(tmp_path: Path):
    snapshot_path = tmp_path / "snapshots.json"
    outcome_path = tmp_path / "outcomes.json"

    append_outcome(
        create_outcome(
            "orphan-1",
            "interview",
        ),
        outcome_path,
    )

    report = generate_validation_report(
        snapshot_path,
        outcome_path,
    )

    assert "Recommendations: 0" in report
    assert "Outcomes without Snapshot: 1" in report
    assert "Recommendation ID: orphan-1" in report
    assert "Outcomes: interview" in report


def test_validation_report_mixed_data_and_orphan_outcome(tmp_path: Path):
    snapshot_path = tmp_path / "snapshots.json"
    outcome_path = tmp_path / "outcomes.json"

    save_snapshot_once(
        _snapshot("linked-1", "Linked Job", 80),
        snapshot_path,
    )
    save_snapshot_once(
        _snapshot("ignored-1", "Ignored Job", 35),
        snapshot_path,
    )
    append_outcome(
        create_outcome(
            "linked-1",
            "saved",
        ),
        outcome_path,
    )
    append_outcome(
        create_outcome(
            "linked-1",
            "offer",
        ),
        outcome_path,
    )
    append_outcome(
        create_outcome(
            "orphan-1",
            "applied",
        ),
        outcome_path,
    )

    report = generate_validation_report(
        snapshot_path,
        outcome_path,
    )

    assert "Recommendations: 2" in report
    assert "Linked Recommendations: 1" in report
    assert "Snapshots without Outcome: 1" in report
    assert "Outcomes without Snapshot: 1" in report
    assert "Outcome: offer" in report
    assert "Job: Linked Job" in report
    assert "Recommendation ID: orphan-1" in report


def test_validation_report_invalid_json_is_empty(tmp_path: Path):
    snapshot_path = tmp_path / "snapshots.json"
    outcome_path = tmp_path / "outcomes.json"
    snapshot_path.write_text("{", encoding="utf-8")
    outcome_path.write_text(json.dumps({}), encoding="utf-8")

    report = generate_validation_report(
        snapshot_path,
        outcome_path,
    )

    assert "Recommendations: 0" in report
