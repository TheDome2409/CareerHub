import re
from dataclasses import replace

from jobagent.services.skill_candidate_domain_service import (
    detect_candidate_domain,
    normalize_candidate_domain,
)


CANDIDATE_TYPES = {
    "skill",
    "role",
    "certification",
    "context",
    "framework",
    "regulation",
    "unknown",
}

ROLE_TERMS = {
    "administrator",
    "architect",
    "consultant",
    "director",
    "engineer",
    "head",
    "lead",
    "manager",
    "specialist",
}

CERTIFICATION_TERMS = {
    "administrator",
    "associate",
    "certification",
    "certified",
    "expert",
    "foundation",
    "practitioner",
    "professional",
}

CONTEXT_TERMS = {
    "abonnements",
    "abteilungen",
    "departments",
    "locations",
    "projekte",
    "projects",
    "standorte",
    "subscriptions",
    "unternehmensnetzwerk",
    "kosten",
}

FRAMEWORK_TERMS = {
    "cobit",
    "itil",
    "prince2",
    "scrum",
    "togaf",
}

REGULATION_TERMS = {
    "ai act",
    "dora",
    "nis2",
}

CANONICAL_PATTERNS = [
    ("Azure Landing Zone", ("azure", "landing", "zone")),
    ("Azure Landing Zone", ("azure", "landing", "zones")),
    ("Cloud Governance", ("cloud", "governance")),
    ("Conditional Access Policies", ("conditional", "access", "policies")),
    ("Data Mesh", ("data", "mesh")),
    ("Data Catalog", ("data", "catalog")),
    ("Data Catalog", ("data", "catalogs")),
    ("Data Governance Framework", ("data", "governance", "framework")),
    ("Data Governance Framework", ("data", "governance", "frameworks")),
    ("Data Products", ("data", "products")),
    ("DORA", ("dora",)),
    ("AI Act", ("ai", "act")),
    ("ESG Reporting", ("esg", "reporting")),
    ("FinOps", ("finops",)),
    ("GitOps", ("gitops",)),
    ("Infrastructure as Code", ("infrastructure", "code")),
    ("LLM Governance", ("large", "language", "models")),
    ("LLM Governance", ("llm", "governance")),
    ("MLOps", ("mlops",)),
    ("NIS2", ("nis2",)),
    ("Platform Engineering", ("platform", "engineering")),
    ("Privileged Access Management", ("privileged", "access", "management")),
    ("Retrieval Augmented Generation", ("retrieval", "augmented", "generation")),
    ("Service Level Objectives", ("service", "level", "objectives")),
    ("Change Advisory Board", ("change", "advisory", "board")),
    ("Vendor Governance", ("vendor", "governance")),
    ("Managed Service Provider", ("managed", "service", "provider")),
    ("Servicekatalog", ("servicekatalog",)),
    ("Servicekatalog", ("servicekatalogs",)),
    ("Problem Management Framework", ("problem", "management", "framework")),
    ("Problem Management Framework", ("problem", "management", "frameworks")),
    ("Terraform", ("terraform",)),
    ("Zero Trust", ("zero", "trust")),
]


def normalize_candidate(value: str) -> str:
    value = (value or "").lower()
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "Ã¤": "ae",
        "Ã¶": "oe",
        "Ã¼": "ue",
        "ÃŸ": "ss",
        "ÃƒÂ¤": "ae",
        "ÃƒÂ¶": "oe",
        "ÃƒÂ¼": "ue",
        "ÃƒÅ¸": "ss",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def _title_candidate(value: str) -> str:
    words = []

    for word in re.split(r"\s+", value.strip()):
        normalized = normalize_candidate(word)

        if normalized in {"as", "of"}:
            words.append(normalized)
        elif normalized in {"dora", "nis2"}:
            words.append(normalized.upper())
        elif normalized in {"gitops", "finops", "mlops"}:
            words.append(normalized[:-3].title() + "Ops")
        else:
            words.append(word[:1].upper() + word[1:])

    return " ".join(words)


def _slug(value: str) -> str:
    value = normalize_candidate(value)
    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value,
    )

    return value.strip("_")


def canonical_name_for(candidate: str) -> str:
    normalized = normalize_candidate(candidate)
    words = set(normalized.split())

    if normalized == "governance":
        return "Governance"

    if words.intersection(CERTIFICATION_TERMS) and words.intersection(
        {
            "azure",
            "microsoft",
            "scrum",
            "terraform",
            "itil",
            "cisco",
        }
    ):
        return _title_candidate(candidate)

    for canonical_name, required_words in CANONICAL_PATTERNS:
        if all(word in words for word in required_words):
            return canonical_name

    if (
        "infrastructure" in words
        and "architect" in words
    ):
        return "Infrastructure Architect"

    return _title_candidate(candidate)


def classify_candidate_type(candidate: str) -> str:
    normalized = normalize_candidate(candidate)
    words = set(normalized.split())

    if normalized == "governance":
        return "context"

    if any(word in CONTEXT_TERMS for word in words):
        return "context"

    if {"azure", "data", "engineer"}.issubset(words):
        return "certification"

    if normalized in FRAMEWORK_TERMS:
        return "framework"

    if normalized in REGULATION_TERMS:
        return "regulation"

    if normalized in {"ai act"}:
        return "regulation"

    if any(word in CERTIFICATION_TERMS for word in words) and (
        "certified" in words
        or "certification" in words
        or len(words.intersection(CERTIFICATION_TERMS)) >= 1
        and len(words) <= 4
    ):
        if words.intersection(
            {
                "terraform",
                "azure",
                "microsoft",
                "scrum",
                "itil",
                "cisco",
            }
        ):
            return "certification"

    if any(word in ROLE_TERMS for word in words):
        return "role"

    if normalized:
        return "skill"

    return "unknown"


def canonicalize_evaluation(evaluation):
    canonical_name = canonical_name_for(
        evaluation.name
    )
    candidate_type = classify_candidate_type(
        evaluation.name
    )
    is_skill = candidate_type == "skill"
    candidate_domain = normalize_candidate_domain(
        getattr(
            evaluation,
            "candidate_domain",
            "unknown",
        )
    )

    if candidate_domain == "unknown":
        candidate_domain = detect_candidate_domain(
            canonical_name
        )

    return replace(
        evaluation,
        canonical_name=canonical_name,
        candidate_type=candidate_type,
        suggested_tag=_slug(canonical_name),
        is_skill=is_skill,
        candidate_domain=candidate_domain,
        accepted=is_skill,
    )


def deduplicate_evaluations(evaluations):
    merged = {}

    for evaluation in evaluations:
        canonical = canonicalize_evaluation(
            evaluation
        )
        key = normalize_candidate(
            canonical.canonical_name
        )

        if key not in merged:
            merged[key] = canonical
            continue

        existing = merged[key]

        if canonical.confidence > existing.confidence:
            merged[key] = replace(
                canonical,
                reason=(
                    canonical.reason
                    or existing.reason
                ),
                document_source=_merge_sources(
                    existing.document_source,
                    canonical.document_source,
                ),
                candidate_domain=(
                    canonical.candidate_domain
                    if canonical.candidate_domain != "unknown"
                    else existing.candidate_domain
                ),
            )
        else:
            merged[key] = replace(
                existing,
                document_source=_merge_sources(
                    existing.document_source,
                    canonical.document_source,
                ),
                candidate_domain=(
                    existing.candidate_domain
                    if existing.candidate_domain != "unknown"
                    else canonical.candidate_domain
                ),
            )

    return list(merged.values())


def _merge_sources(
    first: str,
    second: str,
) -> str:
    sources = []

    for value in [first, second]:
        for source in str(value or "").split(","):
            source = source.strip()

            if source and source not in sources:
                sources.append(source)

    return ", ".join(sources)
