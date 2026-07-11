from jobagent.models.company_profile_match import CompanyProfileMatch
from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.company_matching_config_service import (
    CompanyMatchingConfig,
    load_company_matching_config,
)
from jobagent.services.profile_mission_service import build_profile_mission
from jobagent.services.skill_candidate_domain_service import normalize_domain_text


def _repository(repository: CompanyRepository | None = None) -> CompanyRepository:
    return repository or CompanyRepository()


def _profile_object(profile):
    return getattr(profile, "profile", profile)


def _values(values) -> list[str]:
    return [
        str(value)
        for value in values or []
        if value is not None and str(value).strip()
    ]


def _normalized_set(values) -> set[str]:
    normalized = {
        normalize_domain_text(value)
        for value in _values(values)
        if normalize_domain_text(value)
    }
    expansions = {
        "digitalisierung": "digitalization",
        "digitale transformation": "digital transformation",
        "infrastruktur": "infrastructure",
        "energie": "energy",
        "bahn": "rail",
        "schiene": "rail",
        "technologie": "technology",
    }

    for source, target in expansions.items():
        if source in normalized:
            normalized.add(target)

    return normalized


def _profile_terms(profile) -> set[str]:
    profile = _profile_object(profile)

    if profile is None:
        return set()

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

    return _normalized_set(terms)


def _profile_mission_terms(profile) -> dict[str, set[str]]:
    if profile is None:
        return {
            "mission": set(),
            "domain": set(),
            "technology": set(),
            "work_model": set(),
        }

    mission = build_profile_mission(profile)

    return {
        "mission": _normalized_set(
            mission.mission_keywords
            + mission.preferred_problem_domains
            + [mission.summary]
        ),
        "domain": _normalized_set(
            mission.interest_domains
            + mission.preferred_company_types
            + mission.preferred_problem_domains
        ),
        "technology": _normalized_set(mission.preferred_technologies),
        "work_model": _normalized_set(mission.preferred_work_models),
    }


def _work_model_preferences(profile) -> tuple[set[str], set[str]]:
    profile = _profile_object(profile)
    work_model = getattr(profile, "work_model", None) if profile is not None else None

    if work_model is None:
        return set(), set()

    return (
        _normalized_set(getattr(work_model, "preferred", []) or []),
        _normalized_set(getattr(work_model, "acceptable", []) or []),
    )


def _exclusions(profile) -> set[str]:
    profile = _profile_object(profile)
    exclusions = getattr(profile, "exclusions", None) if profile is not None else None

    if exclusions is None:
        return set()

    values = []
    values.extend(getattr(exclusions, "industries", []) or [])
    values.extend(getattr(exclusions, "employment_models", []) or [])
    values.extend(getattr(exclusions, "requirements", []) or [])

    return _normalized_set(values)


def _draft_terms(draft) -> dict[str, set[str]]:
    if draft is None:
        return {
            "mission": set(),
            "domain": set(),
            "technology": set(),
            "work_model": set(),
            "all": set(),
        }

    mission = _normalized_set(draft.mission_keywords)
    mission.update(_normalized_set([draft.mission, draft.vision, draft.culture]))
    domain = _normalized_set(draft.business_domains + draft.industries)
    technology = _normalized_set(draft.technologies)
    work_model = _normalized_set(draft.work_models)
    all_terms = set()

    for values in [
        mission,
        domain,
        technology,
        work_model,
        _normalized_set(draft.benefits),
        _normalized_set(draft.canonical_concepts),
        _normalized_set(draft.locations),
    ]:
        all_terms.update(values)

    return {
        "mission": mission,
        "domain": domain,
        "technology": technology,
        "work_model": work_model,
        "all": all_terms,
    }


def _overlap(profile_terms: set[str], company_terms: set[str]) -> set[str]:
    matches = set()

    for profile_term in profile_terms:
        for company_term in company_terms:
            if (
                profile_term == company_term
                or profile_term in company_term
                or company_term in profile_term
            ):
                matches.add(company_term)
                continue

            profile_tokens = {
                token
                for token in profile_term.split()
                if len(token) > 4
            }
            company_tokens = {
                token
                for token in company_term.split()
                if len(token) > 4
            }

            if profile_tokens.intersection(company_tokens):
                matches.add(company_term)

    return matches


def _score_overlap(
    profile_terms: set[str],
    company_terms: set[str],
    maximum: int,
) -> tuple[int, set[str]]:
    if not profile_terms or not company_terms:
        return 0, set()

    matches = _overlap(profile_terms, company_terms)

    if not matches:
        return 0, set()

    if matches == company_terms:
        return maximum, matches

    ratio = min(1.0, len(matches) / max(1, min(len(profile_terms), len(company_terms))))

    return int(round(maximum * ratio)), matches


def _score_work_model(
    profile,
    company_terms: set[str],
    config: CompanyMatchingConfig,
) -> tuple[int, list[str], list[str]]:
    preferred, acceptable = _work_model_preferences(profile)

    if not preferred and not acceptable:
        return -config.missing_work_model_penalty, [], [
            "Keine Arbeitsmodell-Praeferenzen im Profil."
        ]

    if not company_terms:
        return -config.missing_work_model_penalty, [], [
            "Kein Arbeitsmodell im Company Knowledge Draft."
        ]

    preferred_matches = _overlap(preferred, company_terms)
    acceptable_matches = _overlap(acceptable, company_terms)

    if preferred_matches:
        return config.work_model_weight, sorted(preferred_matches), []

    if acceptable_matches:
        return int(round(config.work_model_weight * 0.6)), sorted(acceptable_matches), []

    return 0, [], ["Arbeitsmodell passt nicht sichtbar zu den Praeferenzen."]


def _score_kritis(
    profile_terms: set[str],
    draft,
    config: CompanyMatchingConfig,
) -> tuple[int, list[str]]:
    kritis_profile_terms = {
        term
        for term in profile_terms
        if any(keyword in term for keyword in ["kritis", "infrastruktur", "energy", "energie", "grid", "bahn"])
    }
    company_kritis = bool(getattr(draft, "kritis_relevance", False))
    company_concepts = _normalized_set(getattr(draft, "canonical_concepts", []) if draft else [])
    company_kritis = company_kritis or any(
        any(keyword in concept for keyword in ["kritis", "infrastructure", "grid", "rail"])
        for concept in company_concepts
    )

    if kritis_profile_terms and company_kritis:
        return config.kritis_weight, ["Unternehmen zeigt Bezug zu kritischer Infrastruktur."]

    if company_kritis:
        return int(round(config.kritis_weight * 0.5)), ["Unternehmen zeigt KRITIS-/Infrastrukturbezug."]

    return 0, []


def _score_exclusions(
    profile,
    draft,
    config: CompanyMatchingConfig,
) -> tuple[int, list[str], list[str]]:
    excluded = _exclusions(profile)

    if not excluded:
        return 0, [], ["Keine harten Ausschlüsse im Profil."]

    company_terms = _draft_terms(draft)["all"]
    matches = _overlap(excluded, company_terms)

    if not matches:
        return 0, [], ["Keine Ausschlüsse im Unternehmen erkannt."]

    penalty = -min(config.max_exclusion_penalty, 10 * len(matches))

    return penalty, sorted(matches), [
        "Ausschlüsse im Unternehmensprofil erkannt: " + ", ".join(sorted(matches))
    ]


def _confidence(profile, draft, matched_concepts: list[str]) -> float:
    if profile is None:
        return 0.2

    if draft is None:
        return 0.1

    stats = getattr(draft, "concept_statistics", {}) or {}
    concept_count = int(stats.get("canonical") or 0)
    base = 0.35

    if concept_count:
        base += min(0.35, concept_count * 0.04)

    if matched_concepts:
        base += 0.2

    return round(min(0.9, base), 2)


def match_company_to_profile(
    company_id: int,
    profile=None,
    profile_fingerprint: str = "default",
    repository: CompanyRepository | None = None,
) -> CompanyProfileMatch:
    repo = _repository(repository)
    config = load_company_matching_config()
    draft = repo.load_latest_company_knowledge_draft(company_id)
    terms = _draft_terms(draft)
    profile_terms = _profile_terms(profile)
    mission_terms = _profile_mission_terms(profile)
    reasons = []
    risk_flags = []
    missing = []
    matched_concepts = []

    if profile is None or not profile_terms:
        reasons.append("Keine oder nur wenige Profildaten verfügbar; neutraler Match.")
        missing.append("profile_terms")

    if draft is None:
        reasons.append("Kein Company Knowledge Draft vorhanden.")
        missing.append("company_knowledge_draft")

    mission_score, mission_matches = _score_overlap(
        mission_terms["mission"] or profile_terms,
        terms["mission"],
        config.mission_weight,
    )
    domain_score, domain_matches = _score_overlap(
        mission_terms["domain"] or profile_terms,
        terms["domain"],
        config.domain_weight,
    )
    technology_score, technology_matches = _score_overlap(
        mission_terms["technology"] or profile_terms,
        terms["technology"],
        config.technology_weight,
    )
    work_model_score, work_matches, work_missing = _score_work_model(
        profile,
        terms["work_model"],
        config,
    )
    kritis_score, kritis_reasons = _score_kritis(
        profile_terms,
        draft,
        config,
    )
    exclusion_score, exclusion_matches, exclusion_reasons = _score_exclusions(
        profile,
        draft,
        config,
    )

    matched_concepts.extend(sorted(mission_matches | domain_matches | technology_matches))
    matched_concepts.extend(work_matches)
    matched_concepts = sorted(set(matched_concepts))
    missing.extend(work_missing)

    if mission_matches:
        reasons.append("Mission-/Purpose-Bezug: " + ", ".join(sorted(mission_matches)))

    if domain_matches:
        reasons.append("Business-Domain-Match: " + ", ".join(sorted(domain_matches)))

    if technology_matches:
        reasons.append("Technologie-Match: " + ", ".join(sorted(technology_matches)))

    if work_matches:
        reasons.append("Arbeitsmodell passt: " + ", ".join(work_matches))

    reasons.extend(kritis_reasons)
    reasons.extend(exclusion_reasons)

    if exclusion_matches:
        risk_flags.append("Hard Exclusion: " + ", ".join(exclusion_matches))

    raw_score = (
        mission_score
        + domain_score
        + technology_score
        + work_model_score
        + kritis_score
        + exclusion_score
    )
    if not profile_terms:
        raw_score = config.neutral_score_without_profile + exclusion_score

    total_score = int(max(0, min(100, raw_score)))

    if not reasons:
        reasons.append("Keine starken Profil-Company-Überschneidungen erkannt.")

    match = CompanyProfileMatch(
        company_id=company_id,
        profile_fingerprint=profile_fingerprint,
        total_score=total_score,
        mission_score=mission_score,
        domain_score=domain_score,
        technology_score=technology_score,
        work_model_score=work_model_score,
        kritis_score=kritis_score,
        exclusion_score=exclusion_score,
        matched_concepts=matched_concepts,
        missing_profile_preferences=sorted(set(missing)),
        risk_flags=risk_flags,
        reasons=reasons,
        confidence=_confidence(profile, draft, matched_concepts),
    )

    return repo.save_company_profile_match(match)


def match_all_tracked_companies(
    profile=None,
    profile_fingerprint: str = "default",
    repository: CompanyRepository | None = None,
) -> list[CompanyProfileMatch]:
    repo = _repository(repository)
    tracked = repo.list_tracked_companies(profile_fingerprint)

    return [
        match_company_to_profile(
            int(item["company_id"]),
            profile=profile,
            profile_fingerprint=profile_fingerprint,
            repository=repo,
        )
        for item in tracked
    ]
