from types import SimpleNamespace

from jobagent.models.job import Job
from jobagent.services.company_aggregation_service import (
    UNKNOWN_COMPANY,
    aggregate_companies,
)
from jobagent.services.company_match_service import (
    match_companies,
    prioritize_known_companies,
)


def _profile(
    skills=None,
    preferred_roles=None,
    industries=None,
    work_model_preferred=None,
    work_model_acceptable=None,
):
    return SimpleNamespace(
        skills=skills or [],
        certifications=[],
        interests=[],
        preferred_roles=preferred_roles or [],
        exclusions=SimpleNamespace(
            industries=industries or [],
            employment_models=[],
            requirements=[],
        ),
        work_model=SimpleNamespace(
            preferred=work_model_preferred or [],
            acceptable=work_model_acceptable or [],
        ),
    )


def test_aggregate_companies_groups_jobs_by_company():
    jobs = [
        Job(
            title="IT Projektleiter",
            company="CareerHub GmbH",
            location="Koeln",
            work_model="hybrid",
            career_tags=["project_management", "cloud"],
        ),
        Job(
            title="Cloud Consultant",
            company="CareerHub GmbH",
            location="Bonn",
            work_model="remote",
            career_tags=["cloud", "consulting"],
        ),
        Job(
            title="Pflegefachkraft",
            company="Klinik Beispiel",
            career_tags=["patient_care"],
        ),
    ]

    companies = aggregate_companies(
        jobs
    )
    careerhub = next(
        company
        for company in companies
        if company.name == "CareerHub GmbH"
    )

    assert len(companies) == 2
    assert len(careerhub.jobs) == 2
    assert "Koeln" in careerhub.locations
    assert "remote" in careerhub.work_models
    assert "cloud" in careerhub.detected_skills


def test_company_match_scores_relevant_company_above_unmatched_company():
    jobs = [
        Job(
            title="IT Projektleiter",
            company="CareerHub GmbH",
            work_model="hybrid",
            career_tags=[
                "project_management",
                "cloud",
                "digitalization",
            ],
            description="Projektmanagement, Cloud und Digitalisierung.",
        ),
        Job(
            title="Pflegefachkraft",
            company="Klinik Beispiel",
            work_model="onsite",
            career_tags=["patient_care"],
            description="Pflege und Patientendokumentation.",
        ),
    ]
    profile = _profile(
        skills=[
            "project_management",
            "cloud",
            "digitalization",
        ],
        preferred_roles=[
            "IT Projektleiter",
        ],
        work_model_preferred=[
            "hybrid",
        ],
    )

    results = match_companies(
        aggregate_companies(jobs),
        profile,
    )

    assert results[0].company.name == "CareerHub GmbH"
    assert results[0].total_score > results[1].total_score
    assert results[0].skill_coverage_score > 0
    assert results[0].matching_jobs[0].title == "IT Projektleiter"
    assert results[0].application_recommendation.startswith(
        "Konkrete Bewerbung"
    )


def test_company_match_reports_profile_exclusion_risk():
    jobs = [
        Job(
            title="IT Projektleiter",
            company="Defense GmbH",
            industries=["defense"],
            career_tags=["project_management"],
        )
    ]
    profile = _profile(
        skills=["project_management"],
        industries=["defense"],
    )

    result = match_companies(
        aggregate_companies(jobs),
        profile,
    )[0]

    assert result.risk_flags
    assert result.preference_score == 0
    assert result.application_recommendation.startswith(
        "Beobachten"
    )


def test_unknown_company_can_be_sorted_to_the_end():
    jobs = [
        Job(
            title="Unbekannte Anzeige",
            company=None,
            career_tags=["project_management"],
        ),
        Job(
            title="IT Projektleiter",
            company="CareerHub GmbH",
            career_tags=["project_management"],
        ),
    ]
    profile = _profile(
        skills=["project_management"],
    )

    results = match_companies(
        aggregate_companies(jobs),
        profile,
    )
    sorted_results = prioritize_known_companies(
        results
    )

    assert sorted_results[-1].company.name == UNKNOWN_COMPANY
