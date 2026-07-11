from types import SimpleNamespace

from jobagent.models.company import CompanyProfile
from jobagent.services.company_match_service import (
    DEFAULT_COMPANY_MATCH_SCORING,
    match_company,
)
from jobagent.services.company_profile_loader import (
    DEFAULT_COMPANY_PROFILE_DIR,
    load_company_profiles,
)


def _strategic_profile():
    return SimpleNamespace(
        skills=[
            "digitalization",
            "business_analysis",
            "ai_tools",
        ],
        interests=[
            "innovation",
            "artificial_intelligence",
        ],
        preferred_roles=[
            "Digital Transformation Manager",
            "Venture Builder",
        ],
        career_goals=SimpleNamespace(
            short_term=[
                "process_improvement",
            ],
            mid_term=[
                "digital_transformation",
            ],
            long_term=[
                "venture_building",
            ],
        ),
        employer_preferences=SimpleNamespace(
            positive=[
                "innovation",
                "digitalization",
            ],
        ),
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


def _neutral_profile():
    return SimpleNamespace(
        skills=[
            "patient_care",
        ],
        interests=[
            "healthcare",
        ],
        preferred_roles=[
            "Pflegefachkraft",
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


def test_synatix_gets_relevant_strategic_fit_score():
    result = match_company(
        _synatix(),
        _strategic_profile(),
        DEFAULT_COMPANY_MATCH_SCORING,
    )

    assert result.strategic_fit_score == 25
    assert result.total_score == 100
    assert any(
        "Strategic Fit:" in reason
        and "Digitalisierung" in reason
        and "Unternehmertum / Venture Building" in reason
        for reason in result.reasons
    )
    assert "Score auf 100 begrenzt" in result.reasons


def test_company_match_score_cap_keeps_partial_scores():
    result = match_company(
        _synatix(),
        _strategic_profile(),
        DEFAULT_COMPANY_MATCH_SCORING,
    )

    assert result.role_opportunity_score == 12
    assert result.skill_coverage_score == 30
    assert result.competency_coverage_score == 30
    assert result.strategic_fit_score == 25
    assert result.preference_score == 7
    assert result.total_score == 100


def test_company_without_strategic_overlap_gets_zero():
    company = CompanyProfile(
        name="Klinik Beispiel",
        description="Stationaere Pflege und Patientenversorgung.",
        detected_skills=[
            "patient_care",
            "medical_documentation",
        ],
        detected_competencies=[
            "documentation",
        ],
    )

    result = match_company(
        company,
        _strategic_profile(),
        DEFAULT_COMPANY_MATCH_SCORING,
    )

    assert result.strategic_fit_score == 0


def test_existing_company_match_remains_functional_with_strategic_fit():
    result = match_company(
        _synatix(),
        _neutral_profile(),
        DEFAULT_COMPANY_MATCH_SCORING,
    )

    assert result.company.name == "Example Technologies"
    assert result.total_score >= 0
    assert result.strategic_fit_score == 0


def test_company_match_low_score_is_not_capped():
    company = CompanyProfile(
        name="Klinik Beispiel",
        description="Stationaere Pflege und Patientenversorgung.",
    )

    result = match_company(
        company,
        _neutral_profile(),
        DEFAULT_COMPANY_MATCH_SCORING,
    )

    assert result.total_score < 100
    assert "Score auf 100 begrenzt" not in result.reasons
