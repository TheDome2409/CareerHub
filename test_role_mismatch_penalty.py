from pathlib import Path

from jobagent.core.config_loader import (
    load_profile,
    load_scoring,
)
from jobagent.models.job import Job
from jobagent.services.scorer import JobScorer


CONFIG_DIR = Path("config")


def _scoring():
    return load_scoring(
        CONFIG_DIR / "scoring.example.yaml"
    )


def _profile():
    return load_profile(
        CONFIG_DIR / "profile.example.yaml"
    ).profile


def _developer_profile():
    profile = _profile()

    return profile.model_copy(
        update={
            "preferred_roles": [
                "Software Engineer",
                "Ruby Developer",
            ],
            "skills": [
                "ruby",
                "rails",
                "software_development",
            ],
        }
    )


def test_rails_engineer_is_penalized_for_non_developer_profile():
    scorer = JobScorer(
        _profile(),
        _scoring(),
    )
    job = Job(
        title="Tech Lead Full-Stack Rails Engineer",
        company="Mitre Media",
        work_model="remote",
        description=(
            "Rails 8 platform, Ruby, Kubernetes, Redis and LLM "
            "applications."
        ),
        career_tags=[
            "ai",
            "leadership",
            "architecture",
            "innovation",
            "platform",
            "data",
        ],
    )

    result = scorer.score(
        job
    )

    assert result.role_mismatch_penalty == -30
    assert result.total_score <= 30
    assert any(
        "Role Mismatch Penalty: -30" in reason
        for reason in result.reasons
    )


def test_project_manager_role_is_not_penalized():
    scorer = JobScorer(
        _profile(),
        _scoring(),
    )
    job = Job(
        title="IT Project Manager",
        company="CareerHub GmbH",
        work_model="remote",
        description="IT project management and digitalization.",
        career_tags=[
            "project_responsibility",
            "digitalization",
        ],
    )

    result = scorer.score(
        job
    )

    assert result.role_mismatch_penalty == 0
    assert not any(
        "Role Mismatch Penalty" in reason
        for reason in result.reasons
    )


def test_developer_profile_is_not_penalized_for_developer_role():
    scorer = JobScorer(
        _developer_profile(),
        _scoring(),
    )
    job = Job(
        title="Senior Ruby Developer",
        company="Rails GmbH",
        work_model="remote",
        description="Ruby and Rails software development.",
        career_tags=[
            "architecture",
        ],
    )

    result = scorer.score(
        job
    )

    assert result.role_mismatch_penalty == 0
