from types import SimpleNamespace

from jobagent.services.company_match_report_service import (
    generate_company_match_report,
)
from jobagent.services.company_match_service import (
    match_companies,
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


def test_loads_synatix_manual_company_profile():
    profiles = load_company_profiles(
        DEFAULT_COMPANY_PROFILE_DIR
    )
    synatix = next(
        profile
        for profile in profiles
        if profile.name == "Example Technologies"
    )

    assert synatix.source_type == "manual"
    assert "Venture Builder / Company Builder" in synatix.focus_areas
    assert "IT-Projektmanagement" in synatix.possible_use_cases
    assert "software_development" in synatix.detected_skills
    assert "digitalization" in synatix.detected_competencies


def test_manual_synatix_profile_can_be_matched_without_jobs():
    synatix = next(
        profile
        for profile in load_company_profiles(
            DEFAULT_COMPANY_PROFILE_DIR
        )
        if profile.name == "Example Technologies"
    )

    result = match_companies(
        [
            synatix,
        ],
        _profile(),
    )[0]

    assert result.company.name == "Example Technologies"
    assert result.total_score > 0
    assert result.role_opportunity_score > 0
    assert result.skill_coverage_score > 0
    assert result.application_recommendation.startswith(
        "Initiativbewerbung"
    )


def test_synatix_report_uses_manual_possible_use_cases():
    synatix = next(
        profile
        for profile in load_company_profiles(
            DEFAULT_COMPANY_PROFILE_DIR
        )
        if profile.name == "Example Technologies"
    )
    result = match_companies(
        [
            synatix,
        ],
        _profile(),
    )[0]

    report = generate_company_match_report(
        result,
        _profile(),
    )

    assert "IT-Projektmanagement" in report
    assert "Venture Operations" in report
    assert "KI-gest?tzte Tools wie CareerHub" in report
