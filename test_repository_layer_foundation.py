from pathlib import Path

from jobagent.models.global_skill_candidate import GlobalSkillCandidate
from jobagent.models.job import Job
from jobagent.services.global_skill_candidate_service import (
    load_candidates,
    save_candidates,
)
from jobagent.services.recommendation_outcome_service import (
    append_outcome,
    create_outcome,
    get_outcomes_for_recommendation,
    load_outcomes,
)
from jobagent.services.recommendation_snapshot_service import (
    build_recommendation_snapshot,
    load_snapshots,
    save_snapshot_once,
)
from jobagent.services.review_queue_service import (
    load_review_queue,
    save_review_queue,
)
from jobagent.services.validation_report_service import (
    generate_validation_report,
)


def test_review_queue_repository_service_facade(tmp_path: Path):
    import jobagent.services.review_queue_service as service

    path = tmp_path / "review_queue.json"
    entries = [
        {
            "name": "AI",
            "suggested_tag": "artificial_intelligence",
            "candidate_type": "skill",
        }
    ]
    original_path = service.REVIEW_QUEUE_FILE

    try:
        service.REVIEW_QUEUE_FILE = path
        save_review_queue(
            entries,
        )

        assert load_review_queue() == entries
    finally:
        service.REVIEW_QUEUE_FILE = original_path

    assert path.exists()


def test_global_skill_candidate_repository_service_facade(tmp_path: Path):
    path = tmp_path / "global_skill_candidates.json"
    candidates = [
        GlobalSkillCandidate(
            canonical_name="artificial_intelligence",
            aliases=[
                "AI",
                "KI",
            ],
            seen_count=2,
        )
    ]

    save_candidates(
        candidates,
        path,
    )
    loaded = load_candidates(
        path,
    )

    assert loaded[0].canonical_name == "artificial_intelligence"
    assert loaded[0].aliases == [
        "AI",
        "KI",
    ]


def test_snapshot_and_outcome_repositories_link_validation_report(
    tmp_path: Path,
):
    snapshot_path = tmp_path / "recommendation_snapshots.json"
    outcome_path = tmp_path / "recommendation_outcomes.json"
    job = Job(
        title="AI Project Manager",
        company="Future Systems",
    )
    snapshot = build_recommendation_snapshot(
        profile_fingerprint="profile-123",
        job=job,
        score_result={
            "total_score": 72,
            "skill_score": 20,
            "competency_score": 8,
        },
        recommendation_id="rec-1",
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
            "rec-1",
            "interview",
        ),
        outcome_path,
    )

    assert len(load_snapshots(snapshot_path)) == 1
    assert len(load_outcomes(outcome_path)) == 1
    assert len(
        get_outcomes_for_recommendation(
            "rec-1",
            path=outcome_path,
        )
    ) == 1

    report = generate_validation_report(
        snapshot_path,
        outcome_path,
    )

    assert "Recommendations: 1" in report
    assert "Linked Recommendations:" in report
    assert "1" in report
    assert "Outcome: interview" in report


def test_json_repositories_tolerate_empty_and_invalid_files(tmp_path: Path):
    from jobagent.repositories import (
        JsonGlobalSkillCandidateRepository,
        JsonRecommendationOutcomeRepository,
        JsonRecommendationSnapshotRepository,
        JsonReviewQueueRepository,
    )

    for repository_class, method_name in [
        (JsonReviewQueueRepository, "load_entries"),
        (JsonGlobalSkillCandidateRepository, "load_candidates"),
        (JsonRecommendationSnapshotRepository, "load_snapshots"),
        (JsonRecommendationOutcomeRepository, "load_outcomes"),
    ]:
        path = tmp_path / f"{repository_class.__name__}.json"
        path.write_text(
            "",
            encoding="utf-8",
        )
        repository = repository_class(
            path
        )
        assert getattr(
            repository,
            method_name,
        )() == []

        path.write_text(
            "{",
            encoding="utf-8",
        )
        assert getattr(
            repository,
            method_name,
        )() == []


def test_yaml_taxonomy_repository_loads_taxonomy_files(tmp_path: Path):
    from jobagent.repositories import YamlTaxonomyRepository

    taxonomy_dir = tmp_path / "taxonomy"
    taxonomy_dir.mkdir()
    (
        taxonomy_dir / "aliases.yaml"
    ).write_text(
        "aliases:\n  artificial_intelligence:\n    - ai\n    - ki\n",
        encoding="utf-8",
    )
    (
        taxonomy_dir / "competencies.yaml"
    ).write_text(
        "competency_definitions:\n  planning:\n    description: Planung\n",
        encoding="utf-8",
    )
    (
        taxonomy_dir / "qualifications.yaml"
    ).write_text(
        "qualification_rules:\n  - role_pattern: arzt\n",
        encoding="utf-8",
    )
    (
        taxonomy_dir / "job_intelligence.yaml"
    ).write_text(
        "skill_patterns:\n  ai_adoption:\n    - ai adoption\n",
        encoding="utf-8",
    )

    repository = YamlTaxonomyRepository(
        taxonomy_dir
    )

    assert repository.load_aliases() == {
        "artificial_intelligence": {
            "ai",
            "ki",
        }
    }
    assert "competency_definitions" in repository.load_competencies()
    assert "qualification_rules" in repository.load_qualifications()
    assert "skill_patterns" in repository.load_job_intelligence_patterns()


def test_yaml_taxonomy_repository_tolerates_missing_empty_and_invalid_files(
    tmp_path: Path,
):
    from jobagent.repositories import YamlTaxonomyRepository

    taxonomy_dir = tmp_path / "taxonomy"
    taxonomy_dir.mkdir()
    (
        taxonomy_dir / "aliases.yaml"
    ).write_text(
        "{",
        encoding="utf-8",
    )
    (
        taxonomy_dir / "competencies.yaml"
    ).write_text(
        "",
        encoding="utf-8",
    )

    repository = YamlTaxonomyRepository(
        taxonomy_dir
    )

    assert repository.load_aliases() == {}
    assert repository.load_competencies() == {}
    assert repository.load_qualifications() == {}
    assert repository.load_job_intelligence_patterns() == {}
