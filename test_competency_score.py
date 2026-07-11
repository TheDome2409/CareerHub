from types import SimpleNamespace

from jobagent.models.job import Job
from jobagent.services.scorer import MAX_COMPETENCY_SCORE, JobScorer


def _scoring():
    return SimpleNamespace(
        hard_exclusions=SimpleNamespace(
            industries=[],
            employment_models=[],
            requirements=[],
        ),
        roles={},
        work_model={},
        salary={},
        career={},
        weights=SimpleNamespace(
            career_fit=0,
            employer=0,
            skill_fit=25,
        ),
        employer=SimpleNamespace(
            kununu=SimpleNamespace(
                above_4_3=0,
                above_4_0=0,
                above_3_7=0,
                below_3_0=0,
                below_3_5=0,
            ),
            growth=0,
            innovation=0,
            development=0,
        ),
        red_flags={},
    )


def _scorer(skills):
    profile = SimpleNamespace(
        skills=skills,
        certifications=[],
        interests=[],
    )

    return JobScorer(
        profile,
        _scoring(),
    )


def _without_skill_score(scorer):
    scorer._score_skill_fit = lambda job: (
        0,
        set(),
        set(),
        0.0,
    )

    return scorer


def test_competency_score_formula_examples():
    scorer = _scorer([])

    assert scorer._competency_score_from_ratio(0.00) == 0
    assert scorer._competency_score_from_ratio(0.25) == 2
    assert scorer._competency_score_from_ratio(0.50) == 5
    assert scorer._competency_score_from_ratio(0.75) == 8
    assert scorer._competency_score_from_ratio(1.00) == MAX_COMPETENCY_SCORE


def test_business_transformation_lead_gets_visible_bonus():
    scorer = _without_skill_score(
        _scorer(
            [
                "project_management",
                "stakeholder_management",
                "change_management",
                "digitalization",
            ]
        )
    )
    job = Job(
        title="Business Transformation Lead",
        description=(
            "Business transformation, roadmap planning, stakeholder "
            "communication and change management."
        ),
    )

    result = scorer.score(job)

    assert result.competency_score >= 8
    assert result.total_score - result.competency_score >= 0
    assert "Competency Score" in "\n".join(result.reasons)


def test_it_project_manager_gets_light_bonus():
    scorer = _without_skill_score(
        _scorer(
            [
                "technical_documentation",
            ]
        )
    )
    job = Job(
        title="IT Projektleiter",
        description="Projektplanung, Koordination und Kommunikation.",
    )

    result = scorer.score(job)

    assert 0 < result.competency_score < MAX_COMPETENCY_SCORE


def test_pflegefachkraft_gets_no_competency_bonus_for_unmatched_profile():
    scorer = _without_skill_score(
        _scorer(
            [
                "project_management",
            ]
        )
    )
    job = Job(
        title="Pflegefachkraft",
        description="Patientenversorgung und Pflegedokumentation.",
    )

    result = scorer.score(job)

    assert result.competency_score == 0
