from jobagent.models.competency import Competency
from jobagent.models.competency_match import CompetencyMatch
from jobagent.models.job import Job
from jobagent.repositories import YamlTaxonomyRepository


def _taxonomy_data() -> dict:
    return YamlTaxonomyRepository().load_competencies()


def _competency_definitions(data: dict) -> dict[str, Competency]:
    definitions = data.get(
        "competency_definitions",
        {},
    )

    if not isinstance(definitions, dict):
        return {}

    return {
        name: Competency(
            name=name,
            description=str(values.get("description", "") or ""),
            related_competencies=list(
                values.get("related_competencies", []) or []
            ),
            source_skills=list(values.get("source_skills", []) or []),
        )
        for name, values in definitions.items()
        if isinstance(values, dict)
    }


def _mapping(data: dict, key: str) -> dict[str, list[str]]:
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


_TAXONOMY_DATA = _taxonomy_data()
COMPETENCY_DEFINITIONS = _competency_definitions(
    _TAXONOMY_DATA
)
SKILL_COMPETENCY_MAPPING = _mapping(
    _TAXONOMY_DATA,
    "skill_competency_mapping",
)
JOB_COMPETENCY_KEYWORDS = _mapping(
    _TAXONOMY_DATA,
    "job_competency_keywords",
)


def _profile_object(profile):
    return getattr(
        profile,
        "profile",
        profile,
    )


def _normalize(value: str) -> str:
    value = str(value or "").strip().lower()
    replacements = {
        "\u00e4": "ae",
        "\u00f6": "oe",
        "\u00fc": "ue",
        "\u00df": "ss",
        "-": "_",
        " ": "_",
    }

    for source, target in replacements.items():
        value = value.replace(source, target)

    return value


def load_competency_mapping() -> dict[str, list[str]]:
    return {
        skill: list(competencies)
        for skill, competencies in SKILL_COMPETENCY_MAPPING.items()
    }


def _competencies_from_skills(skills) -> dict[str, list[str]]:
    competencies = {}

    for skill in skills or []:
        normalized_skill = _normalize(skill)

        for competency in SKILL_COMPETENCY_MAPPING.get(
            normalized_skill,
            [],
        ):
            competencies.setdefault(
                competency,
                [],
            ).append(str(skill))

    return {
        competency: sorted(set(evidence))
        for competency, evidence in competencies.items()
    }


def extract_profile_competencies(profile) -> dict[str, list[str]]:
    profile = _profile_object(profile)
    skills = list(
        getattr(profile, "skills", []) or []
    )
    skills.extend(
        getattr(profile, "certifications", []) or []
    )
    skills.extend(
        getattr(profile, "interests", []) or []
    )

    return _competencies_from_skills(skills)


def _job_text(job: Job) -> str:
    values = [
        job.title,
        job.description,
    ]
    values.extend(job.requirements)
    values.extend(job.detected_keywords)
    values.extend(job.career_tags)

    return " ".join(
        str(value)
        for value in values
        if value
    ).lower()


def extract_job_competencies(job: Job) -> dict[str, list[str]]:
    competencies = _competencies_from_skills(
        list(job.career_tags)
        + list(job.detected_keywords)
        + list(job.requirements)
    )
    text = _job_text(job)

    for competency, keywords in JOB_COMPETENCY_KEYWORDS.items():
        evidence = [
            keyword
            for keyword in keywords
            if keyword in text
        ]

        if evidence:
            competencies.setdefault(
                competency,
                [],
            ).extend(evidence)

    return {
        competency: sorted(set(evidence))
        for competency, evidence in competencies.items()
    }


def compare_competencies(
    profile_competencies,
    job_competencies,
) -> dict:
    matched = []
    missing = []
    matches = []

    for competency_name, required_evidence in sorted(
        job_competencies.items()
    ):
        profile_evidence = profile_competencies.get(
            competency_name,
            [],
        )
        is_matched = bool(profile_evidence)

        if is_matched:
            matched.append(competency_name)
        else:
            missing.append(competency_name)

        matches.append(
            CompetencyMatch(
                competency_name=competency_name,
                match_ratio=1.0 if is_matched else 0.0,
                evidence_skills=profile_evidence,
                missing_skills=[] if is_matched else required_evidence,
            )
        )

    total = len(matched) + len(missing)
    match_ratio = len(matched) / total if total else 0.0

    return {
        "matched_competencies": matched,
        "missing_competencies": missing,
        "competency_match_ratio": round(match_ratio, 4),
        "matches": matches,
    }
