from pathlib import Path

from jobagent.models.job import Job
from jobagent.services.recommendation_outcome_service import (
    append_outcome,
    create_outcome,
)
from jobagent.services.recommendation_snapshot_service import (
    build_recommendation_snapshot,
    save_snapshot_once,
    stable_recommendation_id,
)
from jobagent.services.validation_report_service import (
    generate_validation_report,
)


def test_snapshot_persistence_deduplicates_and_links_outcome(tmp_path: Path):
    snapshot_path = tmp_path / "recommendation_snapshots.json"
    outcome_path = tmp_path / "recommendation_outcomes.json"
    profile_fingerprint = "profile-123"
    job = Job(
        title="AI Project Manager",
        company="Future Systems",
        url="https://example.test/job",
        query_source="ai project manager",
    )
    score_result = {
        "total_score": 72,
        "skill_score": 20,
        "skill_match_ratio": 0.8,
        "matched_skills": [
            "artificial_intelligence",
            "project_management",
        ],
        "missing_skills": [
            "governance",
        ],
    }
    recommendation_id = stable_recommendation_id(
        profile_fingerprint,
        job,
    )
    snapshot = build_recommendation_snapshot(
        profile_fingerprint=profile_fingerprint,
        job=job,
        score_result=score_result,
        recommendation_id=recommendation_id,
        qualification_status="needs_review",
    )

    save_snapshot_once(
        snapshot,
        snapshot_path,
    )
    save_snapshot_once(
        snapshot,
        snapshot_path,
    )
    append_outcome(
        create_outcome(
            recommendation_id,
            "interview",
        ),
        outcome_path,
    )

    report = generate_validation_report(
        snapshot_path,
        outcome_path,
    )

    assert snapshot_path.exists()
    assert outcome_path.exists()
    assert report.count("Recommendations: 1") == 1
    assert "Outcome: interview" in report
    assert "Job: AI Project Manager" in report
    assert "Qualification: needs_review" in report
