from jobagent.services.skill_candidate_domain_service import (
    detect_candidate_domain,
    normalize_domain_text,
)


MAX_ROLE_QUERIES = 3
MAX_SKILL_QUERIES = 5
MAX_DOMAIN_QUERIES = 2
MAX_TOTAL_QUERIES = 10

ROLE_QUERY_ALIASES = {
    "it project manager": "IT Projektleiter",
    "it projektmanager": "IT Projektleiter",
    "project manager": "Projektmanager",
    "projektmanager": "Projektmanager",
    "projektleiter": "Projektleiter",
}

SKILL_QUERY_ALIASES = {
    "architecture": "Infrastruktur",
    "cloud": "Azure",
    "digitalization": "Digitalisierung",
    "infrastructure": "Infrastruktur",
    "it infrastructure": "Infrastruktur",
    "project management": "Projektmanagement",
    "project_management": "Projektmanagement",
    "project responsibility": "Projektmanagement",
    "project_responsibility": "Projektmanagement",
    "security": "IT Sicherheit",
}

DOMAIN_QUERY_HINTS = {
    "it": [
        "Infrastruktur",
        "Azure",
    ],
    "public_service": [
        "Verwaltungsfachangestellte",
        "Verwaltungsrecht",
    ],
    "legal": [
        "Verwaltungsrecht",
        "Vergaberecht",
    ],
    "craft": [
        "Schornsteinfeger",
        "Gebäudeenergiegesetz",
    ],
    "finance": [
        "Buchhaltung",
        "DATEV",
    ],
    "healthcare": [
        "Entlassungsmanagement",
        "Krankenhausinformationssystem",
    ],
    "education": [
        "Pädagogik",
        "Sprachförderung",
    ],
    "general_business": [
        "Prozessmanagement",
        "Change Management",
    ],
}


def _add_query(
    queries: list[str],
    seen: set[str],
    query: str | None,
) -> None:
    query = (query or "").strip()

    if not query:
        return

    normalized = normalize_domain_text(query)

    if not normalized or normalized in seen:
        return

    seen.add(normalized)
    queries.append(query)


def _role_query(role: str) -> str:
    normalized = normalize_domain_text(role)

    return ROLE_QUERY_ALIASES.get(
        normalized,
        role,
    )


def _skill_query(skill: str) -> str:
    normalized = normalize_domain_text(skill)

    return SKILL_QUERY_ALIASES.get(
        normalized,
        skill,
    )


def _profile_object(profile):
    return getattr(
        profile,
        "profile",
        profile,
    )


def _domain_hints_for(skills: list[str]) -> list[str]:
    domains = []

    for skill in skills:
        domain = detect_candidate_domain(skill)

        if domain != "unknown" and domain not in domains:
            domains.append(domain)

    hints = []

    for domain in domains:
        for hint in DOMAIN_QUERY_HINTS.get(domain, []):
            if hint not in hints:
                hints.append(hint)

    return hints


def build_search_queries(profile) -> list[str]:
    profile = _profile_object(profile)
    queries = []
    seen = set()
    preferred_roles = [
        str(role)
        for role in getattr(profile, "preferred_roles", [])
        if str(role).strip()
    ]
    profile_skills = [
        str(skill)
        for skill in getattr(profile, "skills", [])
        if str(skill).strip()
    ]

    if not preferred_roles and not profile_skills:
        return []

    for role in preferred_roles[:MAX_ROLE_QUERIES]:
        _add_query(
            queries,
            seen,
            _role_query(str(role)),
        )

    skill_query_budget = MAX_SKILL_QUERIES

    for skill in profile_skills:
        if skill_query_budget <= 0:
            break

        before = len(queries)
        _add_query(
            queries,
            seen,
            _skill_query(skill),
        )

        if len(queries) > before:
            skill_query_budget -= 1

    for hint in _domain_hints_for(profile_skills)[:MAX_DOMAIN_QUERIES]:
        _add_query(
            queries,
            seen,
            hint,
        )

    return queries[:MAX_TOTAL_QUERIES]
