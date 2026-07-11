from types import SimpleNamespace

from jobagent.models.job import Job
from jobagent.models.job_intelligence import JobIntelligence
from jobagent.services.qualification_service import (
    evaluate_qualification_gap,
)


def _profile(skills=None, certifications=None, preferred_roles=None):
    return SimpleNamespace(
        skills=skills or [],
        certifications=certifications or [],
        preferred_roles=preferred_roles or [],
    )


def test_business_transformation_lead_needs_review():
    job = Job(
        title="Business Transformation Lead",
        description="Lead business transformation and AI adoption.",
    )
    intelligence = JobIntelligence(
        qualification_requirements=[
            "leadership_experience",
            "senior_experience",
            "transformation_experience",
        ]
    )

    result = evaluate_qualification_gap(
        _profile(),
        job,
        intelligence,
    )

    assert result.qualification_status == "needs_review"
    assert result.qualification_score < 100
    assert len(result.warnings) == 3


def test_pflegefachkraft_education_requires_formal_review():
    job = Job(
        title="Pflegefachkraft",
        description="Stationaere Pflege.",
    )
    intelligence = JobIntelligence(
        qualification_requirements=[
            "education_required",
        ]
    )

    result = evaluate_qualification_gap(
        _profile(),
        job,
        intelligence,
    )

    assert result.qualification_status == "formal_review"
    assert result.qualification_score < 100


def test_it_project_manager_without_intelligence_gap_is_ok():
    job = Job(
        title="IT Projektleiter",
        description="Projektplanung und Koordination.",
    )

    result = evaluate_qualification_gap(
        _profile(),
        job,
    )

    assert result.qualification_status == "ok"
    assert result.warnings == []
    assert result.qualification_score == 100
