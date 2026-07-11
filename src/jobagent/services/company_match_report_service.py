from jobagent.models.company_match_result import CompanyMatchResult
from jobagent.services.competency_service import (
    extract_profile_competencies,
)
from jobagent.services.label_service import (
    get_label,
)
from jobagent.services.skill_candidate_domain_service import (
    normalize_domain_text,
)


def company_match_report_key(result: CompanyMatchResult) -> str:
    company = result.company

    return "|".join(
        [
            normalize_domain_text(company.name),
            str(result.total_score),
            str(len(company.jobs)),
        ]
    )


def _profile_object(profile):
    return getattr(
        profile,
        "profile",
        profile,
    )


def _profile_skills(profile) -> list[str]:
    profile = _profile_object(profile)

    return [
        str(skill).strip()
        for skill in getattr(profile, "skills", []) or []
        if str(skill).strip()
    ]


def _matching_values(profile_values, company_values) -> list[str]:
    company_keys = {
        normalize_domain_text(value)
        for value in company_values or []
        if normalize_domain_text(value)
    }

    return [
        value
        for value in profile_values or []
        if normalize_domain_text(value) in company_keys
    ]


def _labels(values, limit: int = 8) -> str:
    cleaned = [
        get_label(value)
        for value in values or []
        if str(value).strip()
    ][:limit]

    return ", ".join(cleaned) if cleaned else "Keine eindeutigen Signale."


def _job_titles(result: CompanyMatchResult, limit: int = 5) -> list[str]:
    titles = []

    for job in result.matching_jobs[:limit]:
        title = getattr(
            job,
            "title",
            "",
        )

        if title and title not in titles:
            titles.append(title)

    return titles


def _short_conclusion(result: CompanyMatchResult) -> str:
    if result.risk_flags:
        return (
            f"{result.company.name} ist ein Company Match mit "
            f"{result.total_score} Punkten, sollte aber vor einer "
            "Bewerbung wegen offener Risiken geprueft werden."
        )

    if result.total_score >= 60:
        return (
            f"{result.company.name} ist ein starkes Company Match "
            f"mit {result.total_score} Punkten."
        )

    if result.total_score >= 35:
        return (
            f"{result.company.name} zeigt erste passende Signale "
            f"mit {result.total_score} Punkten."
        )

    return (
        f"{result.company.name} ist aktuell eher ein Beobachtungskandidat "
        f"mit {result.total_score} Punkten."
    )


def _interest_reason(result: CompanyMatchResult) -> str:
    parts = []
    company = result.company

    if company.work_models:
        parts.append(
            "Arbeitsmodelle: " + ", ".join(company.work_models)
        )

    if company.locations:
        parts.append(
            "Standorte: " + ", ".join(company.locations[:5])
        )

    if company.focus_areas:
        parts.append(
            "Schwerpunkte: " + _labels(company.focus_areas, limit=6)
        )

    if result.reasons:
        parts.extend(result.reasons[:3])

    if not parts:
        return (
            "Das Unternehmen ist aktuell vor allem durch die "
            "aggregierten Stellenanzeigen im Jobpool sichtbar."
        )

    return "\n".join(
        f"- {part}"
        for part in parts
    )


def _possible_use_cases(result: CompanyMatchResult) -> str:
    if result.company.possible_use_cases:
        return "\n".join(
            f"- {use_case}"
            for use_case in result.company.possible_use_cases[:8]
        )

    titles = _job_titles(
        result
    )

    if titles:
        return "\n".join(
            f"- Umfeld nahe {title}"
            for title in titles
        )

    competencies = result.company.detected_competencies[:5]

    if competencies:
        return "\n".join(
            f"- {get_label(competency)}"
            for competency in competencies
        )

    return "- Noch keine konkreten Einsatzfelder aus den Daten ableitbar."


def _candidate_value(
    result: CompanyMatchResult,
    profile,
) -> str:
    profile_skills = _profile_skills(
        profile
    )
    matching_skills = _matching_values(
        profile_skills,
        result.company.detected_skills,
    )
    profile_competencies = list(
        extract_profile_competencies(profile).keys()
    )
    matching_competencies = _matching_values(
        profile_competencies,
        result.company.detected_competencies,
    )
    lines = []

    if matching_skills:
        lines.append(
            "Skill-Anknuepfung: " + _labels(matching_skills)
        )

    if matching_competencies:
        lines.append(
            "Kompetenz-Anknuepfung: "
            + _labels(matching_competencies)
        )

    if not lines:
        return (
            "Aus dem aktuellen Profil lassen sich noch keine eindeutigen "
            "Mehrwertsignale fuer dieses Unternehmen ableiten."
        )

    return "\n".join(
        f"- {line}"
        for line in lines
    )


def _risks(result: CompanyMatchResult) -> str:
    if result.risk_flags:
        return "\n".join(
            f"- {risk}"
            for risk in result.risk_flags
        )

    if result.company.qualification_requirements:
        return (
            "- Qualifikationsanforderungen pruefen: "
            + _labels(result.company.qualification_requirements)
        )

    return "- Keine expliziten Risiken aus den aktuellen Daten erkannt."


def _pitch(result: CompanyMatchResult, profile) -> str:
    profile_skills = _profile_skills(
        profile
    )
    matching_skills = _matching_values(
        profile_skills,
        result.company.detected_skills,
    )

    if matching_skills:
        return (
            "Ich sehe moegliche Einsatzfelder dort, wo "
            f"{_labels(matching_skills, limit=4)} gefragt sind. "
            "Gern wuerde ich in einem Gespraech ausloten, welche "
            "aktuellen Vorhaben dazu passen."
        )

    return (
        "Ich wuerde gern in einem Gespraech ausloten, ob es passende "
        "Einsatzfelder fuer mein Profil gibt."
    )


def generate_company_match_report(
    result: CompanyMatchResult,
    profile,
) -> str:
    sections = [
        (
            "Kurzfazit",
            _short_conclusion(
                result
            ),
        ),
        (
            "Warum dieses Unternehmen interessant ist",
            _interest_reason(
                result
            ),
        ),
        (
            "Moegliche Einsatzfelder",
            _possible_use_cases(
                result
            ),
        ),
        (
            "Konkreter Mehrwert des Kandidaten",
            _candidate_value(
                result,
                profile,
            ),
        ),
        (
            "Risiken / offene Fragen",
            _risks(
                result
            ),
        ),
        (
            "Gespraechseinstieg / Pitch",
            _pitch(
                result,
                profile,
            ),
        ),
        (
            "Empfohlene Bewerbungsstrategie",
            result.application_recommendation
            or "Beobachten: Noch keine klare Bewerbungsstrategie ableitbar.",
        ),
    ]

    return "\n\n".join(
        f"## {title}\n{body}"
        for title, body in sections
    )
