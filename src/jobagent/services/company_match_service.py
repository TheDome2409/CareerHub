from dataclasses import dataclass
from pathlib import Path

from jobagent.models.company import CompanyProfile
from jobagent.models.company_match_result import CompanyMatchResult
from jobagent.models.job import Job
from jobagent.services.company_aggregation_service import (
    UNKNOWN_COMPANY,
)
from jobagent.services.competency_service import (
    extract_profile_competencies,
)
from jobagent.services.skill_candidate_domain_service import (
    normalize_domain_text,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_COMPANY_MATCH_SCORING_PATH = (
    PROJECT_ROOT / "config" / "company_match_scoring.yaml"
)


@dataclass(frozen=True)
class CompanyMatchScoringConfig:
    role_opportunity_score: int = 25
    skill_coverage_score: int = 30
    competency_coverage_score: int = 30
    strategic_fit_score: int = 25
    preference_score: int = 15
    risk_penalty: int = 10


DEFAULT_COMPANY_MATCH_SCORING = CompanyMatchScoringConfig()


def _as_score_value(value, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback

    return max(
        0,
        parsed,
    )


def _build_scoring_config(raw) -> CompanyMatchScoringConfig:
    if not isinstance(raw, dict):
        return DEFAULT_COMPANY_MATCH_SCORING

    values = raw.get(
        "weights",
        raw,
    )

    if not isinstance(values, dict):
        return DEFAULT_COMPANY_MATCH_SCORING

    defaults = DEFAULT_COMPANY_MATCH_SCORING

    return CompanyMatchScoringConfig(
        role_opportunity_score=_as_score_value(
            values.get("role_opportunity_score"),
            defaults.role_opportunity_score,
        ),
        skill_coverage_score=_as_score_value(
            values.get("skill_coverage_score"),
            defaults.skill_coverage_score,
        ),
        competency_coverage_score=_as_score_value(
            values.get("competency_coverage_score"),
            defaults.competency_coverage_score,
        ),
        strategic_fit_score=_as_score_value(
            values.get("strategic_fit_score"),
            defaults.strategic_fit_score,
        ),
        preference_score=_as_score_value(
            values.get("preference_score"),
            defaults.preference_score,
        ),
        risk_penalty=_as_score_value(
            values.get("risk_penalty"),
            defaults.risk_penalty,
        ),
    )


def load_company_match_scoring_config(
    path: str | Path | None = None,
) -> CompanyMatchScoringConfig:
    if path is None:
        path = DEFAULT_COMPANY_MATCH_SCORING_PATH

    path = Path(path)

    if not path.exists():
        return DEFAULT_COMPANY_MATCH_SCORING

    try:
        import yaml

        loaded = yaml.safe_load(
            path.read_text(encoding="utf-8")
        )
    except Exception:
        return DEFAULT_COMPANY_MATCH_SCORING

    return _build_scoring_config(
        loaded,
    )


def _profile_object(profile):
    return getattr(
        profile,
        "profile",
        profile,
    )


def _normalized_values(values) -> set[str]:
    return {
        normalize_domain_text(value)
        for value in values or []
        if normalize_domain_text(value)
    }


def _profile_skills(profile) -> list[str]:
    profile = _profile_object(profile)

    return [
        str(skill).strip()
        for skill in getattr(profile, "skills", []) or []
        if str(skill).strip()
    ]


def _preferred_roles(profile) -> list[str]:
    profile = _profile_object(profile)

    return [
        str(role).strip()
        for role in getattr(profile, "preferred_roles", []) or []
        if str(role).strip()
    ]


def _profile_exclusions(profile) -> dict[str, list[str]]:
    profile = _profile_object(profile)
    exclusions = getattr(
        profile,
        "exclusions",
        None,
    )

    return {
        "industries": list(
            getattr(exclusions, "industries", []) or []
        ),
        "employment_models": list(
            getattr(exclusions, "employment_models", []) or []
        ),
        "requirements": list(
            getattr(exclusions, "requirements", []) or []
        ),
    }


def _profile_work_model(profile) -> tuple[set[str], set[str]]:
    profile = _profile_object(profile)
    work_model = getattr(
        profile,
        "work_model",
        None,
    )

    preferred = _normalized_values(
        getattr(work_model, "preferred", []) or []
    )
    acceptable = _normalized_values(
        getattr(work_model, "acceptable", []) or []
    )

    return preferred, acceptable


STRATEGIC_THEMES = {
    "Digitalisierung": [
        "digitalization",
        "digital transformation",
        "digitale geschaeftsmodelle",
        "digitalisierung",
        "digitalisierung von prozessen",
    ],
    "Transformation": [
        "transformation",
        "change management",
        "change_management",
        "venture building",
        "company building",
    ],
    "Prozessoptimierung": [
        "process improvement",
        "process_improvement",
        "process analysis",
        "process_analysis",
        "business analysis",
        "business_analysis",
        "prozessoptimierung",
        "digitalisierung von prozessen",
    ],
    "Innovation / KI": [
        "ai",
        "artificial intelligence",
        "innovation",
        "produktentwicklung",
        "product development",
        "ai tools",
        "ai_tools",
        "ki gestuetzte tools",
        "ki tools",
    ],
    "Unternehmertum / Venture Building": [
        "venture builder",
        "venture_builder",
        "company builder",
        "company_builder",
        "beteiligungen",
        "plattformen",
        "platform_business",
        "venture operations",
        "venture_operations",
    ],
}


def _profile_strategic_text(profile) -> str:
    profile = _profile_object(
        profile
    )
    values = []
    career_goals = getattr(
        profile,
        "career_goals",
        None,
    )
    employer_preferences = getattr(
        profile,
        "employer_preferences",
        None,
    )
    scoring_preferences = getattr(
        profile,
        "scoring_preferences",
        None,
    )

    values.extend(
        getattr(profile, "preferred_roles", []) or []
    )
    values.extend(
        getattr(profile, "skills", []) or []
    )
    values.extend(
        getattr(profile, "interests", []) or []
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

    if employer_preferences:
        values.extend(
            getattr(employer_preferences, "positive", []) or []
        )

    if scoring_preferences:
        for name, value in vars(scoring_preferences).items():
            if value == "high":
                values.append(
                    name.replace("_weight", "")
                )

    return normalize_domain_text(
        " ".join(
            str(value)
            for value in values
            if value
        )
    )


def _company_strategic_text(company: CompanyProfile) -> str:
    values = [
        company.name,
        company.description,
        " ".join(company.focus_areas),
        " ".join(company.possible_use_cases),
        " ".join(company.industries),
        " ".join(company.detected_skills),
        " ".join(company.detected_competencies),
    ]

    return normalize_domain_text(
        " ".join(
            str(value)
            for value in values
            if value
        )
    )


def _matched_strategic_themes(
    profile,
    company: CompanyProfile,
) -> list[str]:
    profile_text = _profile_strategic_text(
        profile
    )
    company_text = _company_strategic_text(
        company
    )
    matched = []

    for theme, patterns in STRATEGIC_THEMES.items():
        normalized_patterns = [
            normalize_domain_text(pattern)
            for pattern in patterns
        ]
        profile_match = any(
            pattern and pattern in profile_text
            for pattern in normalized_patterns
        )
        company_match = any(
            pattern and pattern in company_text
            for pattern in normalized_patterns
        )

        if profile_match and company_match:
            matched.append(
                theme
            )

    return matched


def _company_text(company: CompanyProfile) -> str:
    values = [
        company.name,
        company.description,
        " ".join(company.locations),
        " ".join(company.industries),
        " ".join(company.work_models),
        " ".join(company.focus_areas),
        " ".join(company.possible_use_cases),
        " ".join(company.detected_skills),
        " ".join(company.detected_competencies),
        " ".join(company.qualification_requirements),
    ]

    for job in company.jobs:
        values.extend(
            [
                job.title,
                job.description,
                job.location,
                job.work_model,
                " ".join(job.industries),
                " ".join(job.employment_models),
                " ".join(job.requirements),
            ]
        )

    return normalize_domain_text(
        " ".join(
            str(value)
            for value in values
            if value
        )
    )


def _has_text_match(needle: str, haystack: str) -> bool:
    needle = normalize_domain_text(
        needle
    )

    if not needle:
        return False

    return needle in haystack or haystack in needle


def _matching_jobs(
    company: CompanyProfile,
    profile,
) -> list[Job]:
    roles = _preferred_roles(
        profile
    )
    skills = _profile_skills(
        profile
    )
    ranked = []

    for job in company.jobs:
        text = normalize_domain_text(
            " ".join(
                [
                    job.title or "",
                    job.description or "",
                    " ".join(job.career_tags),
                    " ".join(job.detected_keywords),
                ]
            )
        )
        score = 0

        for role in roles:
            if _has_text_match(
                role,
                text,
            ):
                score += 3

        for skill in skills:
            if _has_text_match(
                skill,
                text,
            ):
                score += 1

        ranked.append(
            (
                score,
                job,
            )
        )

    ranked.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return [
        job
        for _score, job in ranked[:5]
    ]


def _score_role_opportunities(
    company: CompanyProfile,
    profile,
    scoring: CompanyMatchScoringConfig,
) -> tuple[int, list[str]]:
    roles = _preferred_roles(
        profile
    )

    if not roles:
        return 0, []

    company_opportunity_text = normalize_domain_text(
        " ".join(
            [
                " ".join(job.title for job in company.jobs),
                " ".join(company.possible_use_cases),
                " ".join(company.focus_areas),
            ]
        )
    )
    matched_roles = [
        role
        for role in roles
        if _has_text_match(
            role,
            company_opportunity_text,
        )
    ]
    ratio = len(matched_roles) / len(roles)

    return round(
        ratio * scoring.role_opportunity_score
    ), matched_roles


def _score_skill_coverage(
    company: CompanyProfile,
    profile,
    scoring: CompanyMatchScoringConfig,
) -> tuple[int, list[str]]:
    profile_skills = _profile_skills(
        profile
    )

    if not profile_skills:
        return 0, []

    company_skills = _normalized_values(
        company.detected_skills
    )
    matched = [
        skill
        for skill in profile_skills
        if normalize_domain_text(skill) in company_skills
    ]
    ratio = len(matched) / len(profile_skills)

    return round(
        ratio * scoring.skill_coverage_score
    ), matched


def _score_competency_coverage(
    company: CompanyProfile,
    profile,
    scoring: CompanyMatchScoringConfig,
) -> tuple[int, list[str]]:
    profile_competencies = set(
        extract_profile_competencies(profile).keys()
    )

    if not profile_competencies:
        return 0, []

    company_competencies = set(
        company.detected_competencies
    )
    matched = sorted(
        profile_competencies.intersection(company_competencies)
    )
    ratio = len(matched) / len(profile_competencies)

    return round(
        ratio * scoring.competency_coverage_score
    ), matched


def _score_strategic_fit(
    company: CompanyProfile,
    profile,
    scoring: CompanyMatchScoringConfig,
) -> tuple[int, list[str]]:
    matched_themes = _matched_strategic_themes(
        profile,
        company,
    )
    score = min(
        scoring.strategic_fit_score,
        len(matched_themes) * 5,
    )

    return score, matched_themes


def _risk_flags(
    company: CompanyProfile,
    profile,
) -> list[str]:
    exclusions = _profile_exclusions(
        profile
    )
    text = _company_text(
        company
    )
    risks = []

    for category, values in exclusions.items():
        for value in values:
            if _has_text_match(
                value,
                text,
            ):
                risks.append(
                    f"Hard Exclusion moeglich: {category}={value}"
                )

    for flag in company.company_intel.red_flags:
        risks.append(
            f"Company Red Flag: {flag}"
        )

    return list(
        dict.fromkeys(risks)
    )


def _score_preferences(
    company: CompanyProfile,
    profile,
    risks: list[str],
    scoring: CompanyMatchScoringConfig,
) -> tuple[int, list[str]]:
    if risks:
        return 0, [
            "Praeferenzscore auf 0 gesetzt, weil Risiken erkannt wurden."
        ]

    preferred, acceptable = _profile_work_model(
        profile
    )
    company_work_models = _normalized_values(
        company.work_models
    )

    if not preferred and not acceptable:
        return scoring.preference_score // 2, [
            "Keine Arbeitsmodell-Praeferenzen im Profil gesetzt."
        ]

    if preferred.intersection(company_work_models):
        return scoring.preference_score, [
            "Bevorzugtes Arbeitsmodell bei dieser Firma gefunden."
        ]

    if acceptable.intersection(company_work_models):
        return round(
            scoring.preference_score * 0.7
        ), [
            "Akzeptables Arbeitsmodell bei dieser Firma gefunden."
        ]

    return 0, [
        "Kein passendes Arbeitsmodell in den aggregierten Jobs erkannt."
    ]


def _application_recommendation(
    total_score: int,
    role_score: int,
    skill_score: int,
    competency_score: int,
    strategic_score: int,
    risks: list[str],
    matching_jobs: list[Job],
) -> str:
    if risks:
        return (
            "Beobachten: Vor einer Bewerbung sollten die erkannten "
            "Risiken oder Ausschluesse geprueft werden."
        )

    if matching_jobs and role_score > 0 and total_score >= 55:
        return (
            "Konkrete Bewerbung: Es gibt passende Jobs als direkte "
            "Einstiegspunkte."
        )

    if total_score >= 45 and (
        skill_score > 0 or competency_score > 0 or strategic_score > 0
    ):
        return (
            "Initiativbewerbung vormerken: Die Firma zeigt passende "
            "Kompetenzsignale, aber noch keinen klaren Zieljob."
        )

    return (
        "Beobachten: Aktuell sind noch wenige belastbare Match-Signale "
        "erkennbar."
    )


def match_company(
    company: CompanyProfile,
    profile,
    scoring: CompanyMatchScoringConfig | None = None,
) -> CompanyMatchResult:
    scoring = scoring or load_company_match_scoring_config()
    role_score, matched_roles = _score_role_opportunities(
        company,
        profile,
        scoring,
    )
    skill_score, matched_skills = _score_skill_coverage(
        company,
        profile,
        scoring,
    )
    competency_score, matched_competencies = _score_competency_coverage(
        company,
        profile,
        scoring,
    )
    strategic_score, matched_strategic_themes = _score_strategic_fit(
        company,
        profile,
        scoring,
    )
    risks = _risk_flags(
        company,
        profile,
    )
    preference_score, preference_reasons = _score_preferences(
        company,
        profile,
        risks,
        scoring,
    )
    raw_score = (
        role_score
        + skill_score
        + competency_score
        + strategic_score
        + preference_score
        - len(risks) * scoring.risk_penalty
    )
    total_score = min(
        100,
        max(
            0,
            raw_score,
        ),
    )
    reasons = []

    if matched_roles:
        reasons.append(
            "Passende Zielrollen: " + ", ".join(matched_roles)
        )

    if matched_skills:
        reasons.append(
            "Skill-Abdeckung: " + ", ".join(matched_skills[:8])
        )

    if matched_competencies:
        reasons.append(
            "Kompetenz-Abdeckung: "
            + ", ".join(matched_competencies[:8])
        )

    if matched_strategic_themes:
        reasons.append(
            "Strategic Fit: " + ", ".join(matched_strategic_themes)
        )

    if raw_score > 100:
        reasons.append(
            "Score auf 100 begrenzt"
        )

    reasons.extend(
        preference_reasons
    )

    if not reasons:
        reasons.append(
            "Noch wenige verwertbare Signale fuer diese Firma erkannt."
        )

    matching_jobs = _matching_jobs(
        company,
        profile,
    )

    return CompanyMatchResult(
        company=company,
        total_score=total_score,
        role_opportunity_score=role_score,
        skill_coverage_score=skill_score,
        competency_coverage_score=competency_score,
        strategic_fit_score=strategic_score,
        preference_score=preference_score,
        risk_flags=risks,
        matching_jobs=matching_jobs,
        application_recommendation=_application_recommendation(
            total_score,
            role_score,
            skill_score,
            competency_score,
            strategic_score,
            risks,
            matching_jobs,
        ),
        reasons=reasons,
    )


def match_companies(
    companies: list[CompanyProfile],
    profile,
) -> list[CompanyMatchResult]:
    scoring = load_company_match_scoring_config()
    results = [
        match_company(
            company,
            profile,
            scoring,
        )
        for company in companies
    ]
    results.sort(
        key=lambda result: result.total_score,
        reverse=True,
    )

    return results


def prioritize_known_companies(
    results: list[CompanyMatchResult],
) -> list[CompanyMatchResult]:
    return sorted(
        results,
        key=lambda result: (
            result.company.name == UNKNOWN_COMPANY,
            -result.total_score,
            result.company.name.lower(),
        ),
    )
