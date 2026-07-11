from jobagent.models.job import Job
from jobagent.models.qualification_requirement import (
    QualificationRequirement,
)
from jobagent.models.qualification_result import QualificationResult
from jobagent.repositories import YamlTaxonomyRepository


def _qualification_data() -> dict:
    return YamlTaxonomyRepository().load_qualifications()


def _requirement(item: dict) -> QualificationRequirement:
    return QualificationRequirement(
        role_pattern=str(item.get("role_pattern", "") or ""),
        requirement_type=item.get("requirement_type", "experience"),
        description=str(item.get("description", "") or ""),
        severity=item.get("severity", "review"),
    )


def _requirements(values) -> list[QualificationRequirement]:
    if not isinstance(values, list):
        return []

    return [
        _requirement(item)
        for item in values
        if isinstance(item, dict)
    ]


def _requirement_map(values) -> dict[str, QualificationRequirement]:
    if not isinstance(values, dict):
        return {}

    return {
        str(key): _requirement(item)
        for key, item in values.items()
        if isinstance(item, dict)
    }


def _string_set(values) -> set[str]:
    if not isinstance(values, list):
        return set()

    return {
        str(value)
        for value in values
        if str(value).strip()
    }


_QUALIFICATION_DATA = _qualification_data()
QUALIFICATION_RULES = _requirements(
    _QUALIFICATION_DATA.get("qualification_rules")
)
JOB_INTELLIGENCE_REQUIREMENT_MAP = _requirement_map(
    _QUALIFICATION_DATA.get("job_intelligence_requirement_map")
)
FORMAL_REVIEW_REQUIREMENT_TYPES = _string_set(
    _QUALIFICATION_DATA.get("formal_review_requirement_types")
)
REGULATED_ROLE_TERMS = _string_set(
    _QUALIFICATION_DATA.get("regulated_role_terms")
)


def _profile_object(profile):
    return getattr(
        profile,
        "profile",
        profile,
    )


def _job_text(job: Job) -> str:
    return " ".join(
        [
            job.title or "",
            job.description or "",
            " ".join(job.requirements),
            " ".join(job.career_tags),
        ]
    ).lower()


def _profile_evidence(profile) -> set[str]:
    profile = _profile_object(profile)
    values = []
    values.extend(
        getattr(profile, "skills", []) or []
    )
    values.extend(
        getattr(profile, "certifications", []) or []
    )
    values.extend(
        getattr(profile, "preferred_roles", []) or []
    )

    career_goals = getattr(
        profile,
        "career_goals",
        None,
    )

    if career_goals:
        values.extend(
            getattr(career_goals, "short_term", []) or []
        )
        values.extend(
            getattr(career_goals, "mid_term", []) or []
        )
        values.extend(
            getattr(career_goals, "long_term", []) or []
        )

    return {
        str(value).strip().lower()
        for value in values
        if str(value).strip()
    }


def _has_requirement_evidence(
    evidence: set[str],
    requirement: QualificationRequirement,
) -> bool:
    evidence_patterns = {
        "leadership": {
            "leadership",
            "fuehrung",
            "team_lead",
            "teamleiter",
            "personalfuehrung",
            "management",
        },
        "experience": {
            "experience",
            "erfahrung",
            "senior",
            "leitung",
            "head_of",
        },
        "education": {
            "ausbildung",
            "studium",
            "degree",
            "bachelor",
            "master",
            "meister",
            "examen",
        },
        "certification": {
            "zertifikat",
            "certification",
            "certified",
        },
        "license": {
            "approbation",
            "berufserlaubnis",
            "license",
            "lizenz",
        },
        "security_clearance": {
            "sicherheitsueberpruefung",
            "security clearance",
            "ue2",
            "ue3",
        },
        "driving_license": {
            "fuehrerschein",
            "drivers license",
            "driving license",
            "klasse b",
        },
    }

    patterns = evidence_patterns.get(
        requirement.requirement_type,
        set(),
    )

    return any(
        pattern in item
        for item in evidence
        for pattern in patterns
    )


def detect_role_requirements(
    job: Job,
) -> list[QualificationRequirement]:
    text = _job_text(job)
    requirements = []

    for rule in QUALIFICATION_RULES:
        if rule.role_pattern in text:
            requirements.append(rule)

    return requirements


def _job_intelligence_object(job, job_intelligence=None):
    if job_intelligence is not None:
        return job_intelligence

    return getattr(
        job,
        "job_intelligence",
        None,
    )


def _job_intelligence_requirement_keys(job, job_intelligence=None) -> list[str]:
    intelligence = _job_intelligence_object(
        job,
        job_intelligence,
    )

    if not intelligence:
        return []

    if isinstance(intelligence, dict):
        values = intelligence.get(
            "qualification_requirements",
            [],
        )
    else:
        values = getattr(
            intelligence,
            "qualification_requirements",
            [],
        )

    return [
        str(value).strip()
        for value in values or []
        if str(value).strip()
    ]


def _job_intelligence_requirements(
    job,
    job_intelligence=None,
) -> list[QualificationRequirement]:
    requirements = []

    for key in _job_intelligence_requirement_keys(
        job,
        job_intelligence,
    ):
        requirement = JOB_INTELLIGENCE_REQUIREMENT_MAP.get(
            key
        )

        if requirement:
            requirements.append(
                requirement
            )

    return requirements


def _deduplicate_requirements(
    requirements: list[QualificationRequirement],
) -> list[QualificationRequirement]:
    deduplicated = {}

    for requirement in requirements:
        key = (
            requirement.requirement_type,
            requirement.description,
        )
        deduplicated.setdefault(
            key,
            requirement,
        )

    return list(
        deduplicated.values()
    )


def _is_regulated_role(job: Job) -> bool:
    text = _job_text(
        job
    )

    return any(
        term in text
        for term in REGULATED_ROLE_TERMS
    )


def _requires_formal_review(
    job: Job,
    missing: list[QualificationRequirement],
) -> bool:
    if any(
        requirement.requirement_type in FORMAL_REVIEW_REQUIREMENT_TYPES
        for requirement in missing
    ):
        return True

    return _is_regulated_role(
        job
    ) and any(
        requirement.requirement_type == "education"
        for requirement in missing
    )


def _qualification_status(
    job: Job,
    missing: list[QualificationRequirement],
) -> str:
    if not missing:
        return "ok"

    if _requires_formal_review(
        job,
        missing,
    ):
        return "formal_review"

    return "needs_review"


def _warning_for_requirement(
    requirement: QualificationRequirement,
) -> str:
    if requirement.requirement_type in {
        "education",
        "license",
        "security_clearance",
    }:
        return f"Formale Qualifikation pruefen: {requirement.description}"

    return f"Qualifikation pruefen: {requirement.description}"


def evaluate_qualification_gap(
    profile,
    job: Job,
    job_intelligence=None,
) -> QualificationResult:
    requirements = _deduplicate_requirements(
        detect_role_requirements(
            job
        )
        + _job_intelligence_requirements(
            job,
            job_intelligence,
        )
    )
    evidence = _profile_evidence(
        profile
    )
    missing = []
    warnings = []

    for requirement in requirements:
        if _has_requirement_evidence(
            evidence,
            requirement,
        ):
            continue

        missing.append(requirement)

        warnings.append(
            _warning_for_requirement(
                requirement
            )
        )

    blocking_missing = [
        requirement
        for requirement in missing
        if requirement.severity == "blocking"
    ]
    review_missing = [
        requirement
        for requirement in missing
        if requirement.severity == "review"
    ]
    warning_missing = [
        requirement
        for requirement in missing
        if requirement.severity == "warning"
    ]
    qualification_score = max(
        0,
        100
        - len(blocking_missing) * 40
        - len(review_missing) * 20
        - len(warning_missing) * 10,
    )
    qualification_status = _qualification_status(
        job,
        missing,
    )

    return QualificationResult(
        eligible=not blocking_missing,
        qualification_status=qualification_status,
        warnings=warnings,
        missing_requirements=missing,
        qualification_score=qualification_score,
    )


def build_qualification_summary(
    result: QualificationResult,
) -> str:
    if not result.missing_requirements:
        return (
            "Keine formalen Qualification Gaps aus den "
            "aktuellen Basisregeln erkannt."
        )

    lines = [
        f"Qualification Score: {result.qualification_score}/100",
    ]

    for requirement in result.missing_requirements:
        lines.append(
            f"- {requirement.requirement_type}: "
            f"{requirement.description} "
            f"({requirement.severity})"
        )

    return "\n".join(lines)
