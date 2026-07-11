from pathlib import Path

from jobagent.core.config_loader import load_profile
from jobagent.models.profile_mission import ProfileMission
from jobagent.services.skill_candidate_domain_service import normalize_domain_text


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROFILE_PATH = PROJECT_ROOT / "config" / "profile.example.yaml"


CONCEPT_RULES = {
    "Digital Workplace": {
        "azure",
        "cloud",
        "microsoft 365",
        "m365",
        "office 365",
        "modern workplace",
    },
    "Business Digitalization": {
        "edi",
        "erp",
        "sap",
        "prozessdigitalisierung",
        "digitalisierung",
        "business analysis",
        "prozessanalyse",
    },
    "Critical Infrastructure": {
        "kritis",
        "infrastruktur",
        "bahn",
        "energie",
        "telekommunikation",
        "grid",
        "netz",
    },
    "Public Digitalization": {
        "verwaltung",
        "public sector",
        "öffentliche hand",
        "egovernment",
        "e-government",
    },
    "Product Innovation": {
        "innovation",
        "produktentwicklung",
        "mvp",
        "prototyping",
        "ki",
        "ai",
        "careerhub",
    },
    "Research and Development": {
        "forschung",
        "research",
        "entwicklung",
        "r&d",
    },
}

TECHNOLOGY_RULES = {
    "Azure": {"azure", "microsoft azure"},
    "Cloud": {"cloud", "landing zone"},
    "SAP / ERP": {"sap", "erp"},
    "EDI": {"edi"},
    "AI Tools": {"ki", "ai", "llm", "ollama", "qwen"},
    "Data Analytics": {"data analytics", "business intelligence", "power bi"},
}

COMPANY_TYPE_RULES = {
    "Critical Infrastructure": {"kritis", "infrastruktur", "bahn", "energie", "telekommunikation"},
    "Public Sector": {"verwaltung", "public sector", "öffentliche hand"},
    "Innovation-driven Company": {"innovation", "produktentwicklung", "venture", "mvp"},
    "Research-oriented Company": {"forschung", "research", "r&d"},
}


def _profile_object(profile):
    return getattr(profile, "profile", profile)


def _values(values) -> list[str]:
    return [
        str(value)
        for value in values or []
        if value is not None and str(value).strip()
    ]


def _collect_terms(profile) -> list[str]:
    profile = _profile_object(profile)

    if profile is None:
        return []

    terms = []
    terms.extend(getattr(profile, "skills", []) or [])
    terms.extend(getattr(profile, "certifications", []) or [])
    terms.extend(getattr(profile, "preferred_roles", []) or [])
    terms.extend(getattr(profile, "interests", []) or [])

    career_goals = getattr(profile, "career_goals", None)

    if career_goals is not None:
        terms.extend(getattr(career_goals, "short_term", []) or [])
        terms.extend(getattr(career_goals, "mid_term", []) or [])
        terms.extend(getattr(career_goals, "long_term", []) or [])

    employer_preferences = getattr(profile, "employer_preferences", None)

    if employer_preferences is not None:
        terms.extend(getattr(employer_preferences, "positive", []) or [])

    return _values(terms)


def _normalized_terms(profile) -> set[str]:
    return {
        normalize_domain_text(term)
        for term in _collect_terms(profile)
        if normalize_domain_text(term)
    }


def _matches_any(terms: set[str], keywords: set[str]) -> bool:
    normalized_keywords = {
        normalize_domain_text(keyword)
        for keyword in keywords
    }

    for term in terms:
        for keyword in normalized_keywords:
            if keyword and (keyword in term or term in keyword):
                return True

    return False


def _matched_labels(terms: set[str], rules: dict[str, set[str]]) -> list[str]:
    return [
        label
        for label, keywords in rules.items()
        if _matches_any(terms, keywords)
    ]


def _work_models(profile) -> list[str]:
    profile = _profile_object(profile)
    work_model = getattr(profile, "work_model", None) if profile is not None else None

    if work_model is None:
        return []

    values = []
    values.extend(getattr(work_model, "preferred", []) or [])
    values.extend(getattr(work_model, "acceptable", []) or [])

    return _dedupe(values)


def _dedupe(values) -> list[str]:
    seen = set()
    result = []

    for value in values or []:
        key = normalize_domain_text(value)

        if not key or key in seen:
            continue

        seen.add(key)
        result.append(str(value))

    return result


def _affinity(terms: set[str], keywords: set[str]) -> float:
    if not terms:
        return 0.0

    return 1.0 if _matches_any(terms, keywords) else 0.0


def _summary(mission_keywords: list[str], preferred_problem_domains: list[str]) -> str:
    if "Critical Infrastructure" in mission_keywords:
        return (
            "Der Nutzer möchte komplexe technische Infrastruktur durch "
            "Digitalisierung robuster, sicherer und effizienter gestalten."
        )

    if "Business Digitalization" in mission_keywords:
        return (
            "Der Nutzer möchte Geschäftsprozesse durch digitale Lösungen "
            "strukturierter, effizienter und entscheidungsfähiger machen."
        )

    if "Product Innovation" in mission_keywords:
        return (
            "Der Nutzer möchte technische Ideen in nutzbare digitale Produkte "
            "und nachvollziehbare Lösungen überführen."
        )

    if preferred_problem_domains:
        return (
            "Der Nutzer möchte seine Erfahrung gezielt in "
            + ", ".join(preferred_problem_domains[:3])
            + " einbringen."
        )

    return "Der Nutzer sucht Aufgaben mit sinnvoller technischer und organisatorischer Wirkung."


def _confidence(terms: set[str], mission_keywords: list[str]) -> float:
    if not terms:
        return 0.2

    return round(
        min(
            0.9,
            0.35 + len(mission_keywords) * 0.1 + min(len(terms), 12) * 0.02,
        ),
        2,
    )


def build_profile_mission(profile) -> ProfileMission:
    terms = _normalized_terms(profile)
    mission_keywords = _matched_labels(terms, CONCEPT_RULES)
    preferred_technologies = _matched_labels(terms, TECHNOLOGY_RULES)
    preferred_company_types = _matched_labels(terms, COMPANY_TYPE_RULES)
    interest_domains = [
        value
        for value in mission_keywords
        if value
        in {
            "Critical Infrastructure",
            "Public Digitalization",
            "Business Digitalization",
            "Research and Development",
        }
    ]
    preferred_problem_domains = [
        value
        for value in mission_keywords
        if value
        in {
            "Business Digitalization",
            "Critical Infrastructure",
            "Product Innovation",
            "Digital Workplace",
        }
    ]

    return ProfileMission(
        summary=_summary(mission_keywords, preferred_problem_domains),
        mission_keywords=mission_keywords,
        interest_domains=interest_domains,
        preferred_problem_domains=preferred_problem_domains,
        preferred_technologies=preferred_technologies,
        preferred_work_models=_work_models(profile),
        preferred_company_types=preferred_company_types,
        kritis_affinity=_affinity(terms, CONCEPT_RULES["Critical Infrastructure"]),
        innovation_affinity=_affinity(terms, CONCEPT_RULES["Product Innovation"]),
        public_sector_affinity=_affinity(terms, CONCEPT_RULES["Public Digitalization"]),
        research_affinity=_affinity(terms, CONCEPT_RULES["Research and Development"]),
        confidence=_confidence(terms, mission_keywords),
    )


def load_profile_mission(profile=None) -> ProfileMission:
    if profile is not None:
        return build_profile_mission(profile)

    try:
        loaded_profile = load_profile(DEFAULT_PROFILE_PATH)
    except Exception:
        loaded_profile = None

    return build_profile_mission(loaded_profile)
