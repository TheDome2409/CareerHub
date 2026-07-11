import re

from jobagent.models.job import Job
from jobagent.models.job_intelligence import JobIntelligence
from jobagent.repositories import YamlTaxonomyRepository
from jobagent.services.competency_service import (
    extract_job_competencies as extract_heuristic_job_competencies,
    load_competency_mapping,
)
from jobagent.services.keyword_detector import (
    detect_keyword_matches,
)
from jobagent.services.skill_alias_service import (
    canonicalize_skill,
)
from jobagent.services.skill_candidate_domain_service import (
    normalize_domain_text,
)


def _patterns(key: str) -> dict[str, list[str]]:
    data = YamlTaxonomyRepository().load_job_intelligence_patterns()
    values = data.get(
        key,
        {},
    )

    if not isinstance(values, dict):
        return {}

    return {
        str(name): [
            str(item)
            for item in items or []
            if str(item).strip()
        ]
        for name, items in values.items()
        if isinstance(items, list)
    }


SKILL_PATTERNS = _patterns(
    "skill_patterns"
)
QUALIFICATION_PATTERNS = _patterns(
    "qualification_patterns"
)
EVIDENCE_PATTERNS = _patterns(
    "evidence_patterns"
)


def _job_text(job: Job) -> str:
    values = [
        job.title,
        job.description,
        " ".join(job.requirements),
        " ".join(job.detected_keywords),
        " ".join(job.career_tags),
    ]

    return " ".join(
        str(value)
        for value in values
        if value
    )


def _normalized_text(job: Job) -> str:
    return normalize_domain_text(
        _job_text(job)
    )


def _pattern_matches(text: str, patterns: list[str]) -> bool:
    normalized_patterns = [
        normalize_domain_text(pattern)
        for pattern in patterns
    ]

    return any(
        pattern in text
        for pattern in normalized_patterns
    )


def _extract_from_patterns(
    job: Job,
    patterns: dict[str, list[str]],
) -> list[str]:
    text = _normalized_text(
        job
    )

    return sorted(
        key
        for key, values in patterns.items()
        if _pattern_matches(text, values)
    )


def _normalize_skill(skill: str) -> str:
    normalized = re.sub(
        r"_+",
        "_",
        normalize_domain_text(skill).replace(" ", "_"),
    ).strip("_")

    return canonicalize_skill(
        normalized
    )


def extract_job_skills(job: Job) -> list[str]:
    text = _job_text(
        job
    )
    skills = {
        _normalize_skill(tag)
        for tag in detect_keyword_matches(text)
        if str(tag).strip()
    }
    skills.update(
        _extract_from_patterns(
            job,
            SKILL_PATTERNS,
        )
    )
    skills.update(
        _normalize_skill(tag)
        for tag in job.career_tags
        if str(tag).strip()
    )

    return sorted(
        skill
        for skill in skills
        if skill
    )


def extract_job_competencies(
    job: Job,
    extracted_skills: list[str] | None = None,
) -> list[str]:
    skills = extracted_skills or extract_job_skills(
        job
    )
    mapping = load_competency_mapping()
    competencies = set(
        extract_heuristic_job_competencies(
            job
        ).keys()
    )

    for skill in skills:
        competencies.update(
            mapping.get(
                _normalize_skill(skill),
                [],
            )
        )

    if "business_transformation" in skills:
        competencies.update(
            {
                "planning",
                "coordination",
                "communication",
                "stakeholder_management",
                "change_management",
            }
        )

    if "roadmap_development" in skills:
        competencies.add(
            "planning"
        )

    if "ai_adoption" in skills:
        competencies.update(
            {
                "digitalization",
                "change_management",
            }
        )

    return sorted(
        competencies
    )


def extract_qualification_requirements(job: Job) -> list[str]:
    requirements = set(
        _extract_from_patterns(
            job,
            QUALIFICATION_PATTERNS,
        )
    )
    text = _normalized_text(
        job
    )

    if re.search(r"\b(8|9|10|[1-9][0-9])\+?\s*(years|jahre)", text):
        requirements.add(
            "senior_experience"
        )

    if "lead" in text or "leitung" in text:
        requirements.add(
            "leadership_experience"
        )

    if "transformation" in text:
        requirements.add(
            "transformation_experience"
        )

    return sorted(
        requirements
    )


def extract_evidence_requirements(job: Job) -> list[str]:
    return _extract_from_patterns(
        job,
        EVIDENCE_PATTERNS,
    )


def _confidence(
    skills: list[str],
    competencies: list[str],
    qualifications: list[str],
    evidence: list[str],
) -> float:
    signal_count = (
        len(skills)
        + len(competencies)
        + len(qualifications)
        + len(evidence)
    )

    if not signal_count:
        return 0.0

    return min(
        0.95,
        round(0.35 + signal_count * 0.05, 2),
    )


def analyze_job(job: Job) -> JobIntelligence:
    skills = extract_job_skills(
        job
    )
    competencies = extract_job_competencies(
        job,
        skills,
    )
    qualifications = extract_qualification_requirements(
        job
    )
    evidence = extract_evidence_requirements(
        job
    )

    return JobIntelligence(
        extracted_skills=skills,
        extracted_competencies=competencies,
        qualification_requirements=qualifications,
        evidence_requirements=evidence,
        confidence=_confidence(
            skills,
            competencies,
            qualifications,
            evidence,
        ),
    )
