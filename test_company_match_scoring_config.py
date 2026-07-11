from types import SimpleNamespace

from jobagent.services.company_match_service import (
    DEFAULT_COMPANY_MATCH_SCORING,
    load_company_match_scoring_config,
    match_company,
)
from jobagent.services.company_profile_loader import (
    DEFAULT_COMPANY_PROFILE_DIR,
    load_company_profiles,
)


def _profile():
    return SimpleNamespace(
        skills=[
            "project_management",
            "digitalization",
            "business_analysis",
        ],
        certifications=[],
        interests=[],
        preferred_roles=[
            "IT-Projektmanagement",
            "Digitalisierung",
        ],
        exclusions=SimpleNamespace(
            industries=[],
            employment_models=[],
            requirements=[],
        ),
        work_model=SimpleNamespace(
            preferred=[],
            acceptable=[],
        ),
    )


def _synatix():
    return next(
        profile
        for profile in load_company_profiles(
            DEFAULT_COMPANY_PROFILE_DIR
        )
        if profile.name == "Example Technologies"
    )


def test_company_match_default_config_keeps_synatix_score():
    result = match_company(
        _synatix(),
        _profile(),
        DEFAULT_COMPANY_MATCH_SCORING,
    )

    assert result.role_opportunity_score == 25
    assert result.skill_coverage_score == 30
    assert result.competency_coverage_score == 30
    assert result.strategic_fit_score == 10
    assert result.preference_score == 7
    assert result.total_score == 100


def test_company_match_custom_config_weights_change_score(tmp_path):
    config_path = tmp_path / "company_match_scoring.yaml"
    config_path.write_text(
        "\n".join(
            [
                "role_opportunity_score: 10",
                "skill_coverage_score: 20",
                "competency_coverage_score: 40",
                "strategic_fit_score: 5",
                "preference_score: 20",
                "risk_penalty: 10",
            ]
        ),
        encoding="utf-8",
    )
    scoring = load_company_match_scoring_config(
        config_path
    )

    result = match_company(
        _synatix(),
        _profile(),
        scoring,
    )

    assert result.role_opportunity_score == 10
    assert result.skill_coverage_score == 20
    assert result.competency_coverage_score == 40
    assert result.strategic_fit_score == 5
    assert result.preference_score == 10
    assert result.total_score == 85


def test_company_match_missing_config_uses_safe_defaults(tmp_path):
    missing_path = tmp_path / "missing_company_match_scoring.yaml"

    scoring = load_company_match_scoring_config(
        missing_path
    )

    assert scoring == DEFAULT_COMPANY_MATCH_SCORING


def test_company_match_invalid_config_uses_safe_defaults(tmp_path):
    invalid_path = tmp_path / "company_match_scoring.yaml"
    invalid_path.write_text(
        "role_opportunity_score: [",
        encoding="utf-8",
    )

    scoring = load_company_match_scoring_config(
        invalid_path
    )

    assert scoring == DEFAULT_COMPANY_MATCH_SCORING
