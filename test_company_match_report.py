from types import SimpleNamespace

from jobagent.models.company import CompanyProfile
from jobagent.models.company_match_result import CompanyMatchResult
from jobagent.models.job import Job
from jobagent.services.company_match_report_service import (
    company_match_report_key,
    generate_company_match_report,
)


def _profile():
    return SimpleNamespace(
        skills=[
            "project_management",
            "cloud",
        ],
        certifications=[],
        interests=[],
    )


def _result():
    company = CompanyProfile(
        name="CareerHub GmbH",
        jobs=[
            Job(
                title="IT Projektleiter",
                company="CareerHub GmbH",
                work_model="remote",
            )
        ],
        locations=[
            "Koeln",
        ],
        work_models=[
            "remote",
        ],
        detected_skills=[
            "project_management",
            "cloud",
        ],
        detected_competencies=[
            "planning",
            "coordination",
        ],
        qualification_requirements=[],
    )

    return CompanyMatchResult(
        company=company,
        total_score=82,
        skill_coverage_score=30,
        competency_coverage_score=20,
        preference_score=15,
        matching_jobs=company.jobs,
        reasons=[
            "Skill-Abdeckung: project_management, cloud",
        ],
        application_recommendation=(
            "Konkrete Bewerbung: Es gibt passende Jobs als direkte "
            "Einstiegspunkte."
        ),
    )


def test_company_match_report_contains_required_sections():
    report = generate_company_match_report(
        _result(),
        _profile(),
    )

    for title in [
        "Kurzfazit",
        "Warum dieses Unternehmen interessant ist",
        "Moegliche Einsatzfelder",
        "Konkreter Mehrwert des Kandidaten",
        "Risiken / offene Fragen",
        "Gespraechseinstieg / Pitch",
        "Empfohlene Bewerbungsstrategie",
    ]:
        assert f"## {title}" in report

    assert "CareerHub GmbH" in report
    assert "Projektmanagement" in report
    assert "Cloud" in report
    assert "IT Projektleiter" in report


def test_company_match_report_does_not_invent_unseen_facts():
    report = generate_company_match_report(
        _result(),
        _profile(),
    ).lower()

    forbidden_terms = [
        "budgetverantwortung",
        "umsatz",
        "mitarbeiterverantwortung",
        "zertifikat",
        "master",
        "bachelor",
    ]

    for term in forbidden_terms:
        assert term not in report


def test_company_match_report_key_is_stable_for_same_result():
    result = _result()

    assert company_match_report_key(result) == company_match_report_key(
        result
    )
