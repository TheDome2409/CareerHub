import re
from html import unescape

from jobagent.services.skill_candidate_domain_service import (
    domain_keywords,
    has_domain_term_pattern,
)
from jobagent.services.taxonomy_loader import load_taxonomy


DOMAIN_SKILL_KEYWORDS = domain_keywords()

STOPWORDS = {
    "am", "an", "als", "auf", "aus", "bei", "das", "dem",
    "den", "der", "des", "die", "durch", "ein", "eine",
    "einem", "einen", "einer", "fuer", "für", "im", "in",
    "mit", "nach", "oder", "und", "von", "zur", "zum",
}

GENERIC_SINGLE_WORDS = {
    "architect", "aufbau", "bewertung", "conditional",
    "definition", "durchfuehrung", "durchführung",
    "einfuehrung", "einführung", "entwicklung",
    "governance", "management", "mitarbeit", "prozesse",
    "projekten", "projekte", "schwerpunkt", "service",
    "services",
    "steuerung", "taetigkeit", "tätigkeit", "unterstuetzung",
    "unterstützung", "weiterbildungen", "zertifikate",
    "zusammenarbeit",
}

NOISE_SINGLE_TERMS = {
    "anliegen",
    "aufgaben",
    "buerger",
    "bürger",
    "gebaeude",
    "gebäude",
    "kunden",
    "medikamenten",
    "projekttagen",
    "unterlagen",
    "verantwortung",
}

PHRASE_STOPWORDS = STOPWORDS.union(
    {
        "anforderung", "anforderungen", "aufbau", "bereich",
        "betriebsmodell", "betriebsmodells", "bewertung",
        "definition", "durchfuehrung", "durchführung",
        "eines", "einer", "einem", "einfuehrung",
        "einführung", "entwicklung", "erfahrung",
        "etablierung", "externer", "externen",
        "internationale", "initiative",
        "initiativen", "kenntnisse", "kontext", "leitung",
        "loesung", "loesungen", "lösung", "lösungen",
        "kosten",
        "modell", "modells", "modelle", "plattform", "projekt",
        "projekte", "projekten", "standorte", "strategie",
        "strategien", "steuerung", "thema", "themen",
        "umfeld", "umgebung", "umsetzung",
        "unternehmensnetzwerk", "unterstuetzung",
        "unterstützung",
    }
)

SKILL_HINTS = (
    "administration", "analyse", "automation", "beratung",
    "cloud", "edi", "erp", "governance", "infrastruktur",
    "integration", "management", "planung", "prozess",
    "projekt", "security", "service", "steuerung",
    "support", "system", "training", "verantwortung",
)

MULTIWORD_SIGNALS = {
    "access", "act", "advisory", "agreement", "agreements",
    "augmented", "azure", "board", "catalog", "catalogs",
    "change", "cloud", "code", "cobit", "compliance",
    "continual", "data", "dora", "enablement",
    "engineering", "esg", "finops", "generation",
    "gitops", "governance", "identity", "improvement",
    "infrastructure", "itil", "kubernetes", "landing",
    "language", "level", "llm", "managed", "mesh",
    "mlops", "models", "nis2", "objectives",
    "operational", "platform", "policies", "prince2",
    "privileged", "problem", "products", "provider",
    "reporting", "retrieval", "reviews", "scrum",
    "security", "service", "servicekatalog",
    "servicekatalogs", "terraform", "togaf", "trust",
    "vendor", "zero", "zone",
}

STRONG_STANDALONE_SKILLS = {
    "cobit", "dora", "finops", "gitops", "itil",
    "kubernetes", "mlops", "nis2", "prince2", "scrum",
    "terraform", "togaf",
}

PREFERRED_MULTIWORD_SKILLS = {
    "ai act", "azure landing zone", "change advisory board",
    "change enablement", "cloud governance",
    "conditional access policies", "continual improvement",
    "data catalog", "data governance framework", "data mesh",
    "data products", "esg reporting", "infrastructure as code",
    "llm governance", "managed service provider",
    "operational level agreements", "platform engineering",
    "problem management framework",
    "retrieval augmented generation",
    "service level objectives", "service reviews",
    "servicekatalog", "vendor governance", "zero trust",
}

NOISE_MULTIWORD_CANDIDATES = {
    "advisory boards",
    "governance frameworks",
    "landing zones",
    "landing zones platform",
    "language models",
    "large language",
    "trust privileged",
    "trust privileged access",
    "zones platform",
}

CANONICAL_PHRASE_PATTERNS = [
    ("AI Act", ("ai", "act")),
    ("Azure Landing Zone", ("azure", "landing", "zone")),
    ("Azure Landing Zone", ("azure", "landing", "zones")),
    ("Change Advisory Board", ("change", "advisory", "board")),
    ("Change Advisory Board", ("change", "advisory", "boards")),
    ("Change Enablement", ("change", "enablement")),
    ("Cloud Governance", ("cloud", "governance")),
    ("Conditional Access Policies", ("conditional", "access", "policies")),
    ("Continual Improvement", ("continual", "improvement")),
    ("Data Catalog", ("data", "catalog")),
    ("Data Catalog", ("data", "catalogs")),
    ("Data Governance Framework", ("data", "governance", "framework")),
    ("Data Governance Framework", ("data", "governance", "frameworks")),
    ("Data Mesh", ("data", "mesh")),
    ("Data Products", ("data", "products")),
    ("ESG Reporting", ("esg", "reporting")),
    ("Infrastructure as Code", ("infrastructure", "code")),
    ("LLM Governance", ("large", "language", "models")),
    ("Managed Service Provider", ("managed", "service", "provider")),
    ("MLOps", ("mlops",)),
    ("Operational Level Agreements", ("operational", "level", "agreements")),
    ("Platform Engineering", ("platform", "engineering")),
    ("Privileged Access Management", ("privileged", "access", "management")),
    ("Problem Management Framework", ("problem", "management", "framework")),
    ("Problem Management Framework", ("problem", "management", "frameworks")),
    ("Retrieval Augmented Generation", ("retrieval", "augmented", "generation")),
    ("Service Level Objectives", ("service", "level", "objectives")),
    ("Service Reviews", ("service", "reviews")),
    ("Servicekatalog", ("servicekatalog",)),
    ("Servicekatalog", ("servicekatalogs",)),
    ("Vendor Governance", ("vendor", "governance")),
    ("Zero Trust", ("zero", "trust")),
]


def _normalize_candidate(value: str) -> str:
    value = unescape(value or "").lower()
    value = value.replace("ä", "ae")
    value = value.replace("ö", "oe")
    value = value.replace("ü", "ue")
    value = value.replace("ß", "ss")
    replacements = {
        "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
        "Ã¤": "ae", "Ã¶": "oe", "Ã¼": "ue", "ÃŸ": "ss",
        "ÃƒÂ¤": "ae", "ÃƒÂ¶": "oe", "ÃƒÂ¼": "ue",
        "ÃƒÅ¸": "ss",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = re.sub(r"[^a-z0-9]+", " ", value)

    return re.sub(r"\s+", " ", value).strip()


def _known_keywords() -> set[str]:
    taxonomy = load_taxonomy()
    keywords = set()

    for tag, data in taxonomy.items():
        keywords.add(_normalize_candidate(tag))
        label = data.get("label")

        if label:
            keywords.add(_normalize_candidate(label))

        for keyword in data.get("keywords", []):
            keywords.add(_normalize_candidate(keyword))

    return {keyword for keyword in keywords if keyword}


def _tokenize_terms(text: str) -> list[str]:
    text = unescape(text or "")
    text = re.sub(r"(?<=[A-Za-z0-9])[-–—](?=[A-Za-z0-9])", " ", text)
    text = re.sub(r"[/|_]+", " ", text)

    return re.findall(
        r"[A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9+.#]*",
        text,
    )


def _tokenize_lines(text: str) -> list[list[str]]:
    lines = []

    for line in (text or "").splitlines():
        tokens = _tokenize_terms(line)

        if tokens:
            lines.append(tokens)

    return lines


def _display_candidate(tokens: list[str]) -> str:
    return " ".join(tokens).strip()


def _trim_candidate_tokens(tokens: list[str]) -> list[str]:
    trimmed = list(tokens)

    while trimmed and _normalize_candidate(trimmed[0]) in PHRASE_STOPWORDS:
        trimmed.pop(0)

    while trimmed and _normalize_candidate(trimmed[-1]) in PHRASE_STOPWORDS:
        trimmed.pop()

    return trimmed


def _canonical_phrase(candidate: str) -> str | None:
    normalized = _normalize_candidate(candidate)
    words = set(normalized.split())

    if "dora" in words:
        return "DORA"

    if "finops" in words:
        return "FinOps"

    if "gitops" in words:
        return "GitOps"

    if "itil" in words:
        return "ITIL"

    if "servicekatalog" in words or "servicekatalogs" in words:
        return "Servicekatalog"

    if "nis2" in words:
        return "NIS2"

    if "terraform" in words:
        return "Terraform"

    if len(words) == 1 and normalized.endswith("bescheide"):
        return _display_candidate(
            [
                candidate[:-1],
            ]
        )

    for canonical, required_words in CANONICAL_PHRASE_PATTERNS:
        if all(word in words for word in required_words):
            return canonical

    return None


def _is_known_candidate(candidate: str, known_keywords: set[str]) -> bool:
    return _normalize_candidate(candidate) in known_keywords


def _phrase_has_signal(words: list[str]) -> bool:
    return any(
        word in MULTIWORD_SIGNALS or word in STRONG_STANDALONE_SKILLS
        for word in words
    )


def _is_useful_multiword_candidate(
    candidate: str,
    known_keywords: set[str],
) -> bool:
    canonical = _canonical_phrase(candidate)

    if canonical:
        return not _is_known_candidate(canonical, known_keywords)

    if _is_known_candidate(candidate, known_keywords):
        return False

    words = [word for word in _normalize_candidate(candidate).split() if word]
    normalized = " ".join(words)

    if normalized in NOISE_MULTIWORD_CANDIDATES:
        return False

    if normalized in DOMAIN_SKILL_KEYWORDS:
        return True

    if len(words) < 2:
        return False

    content_words = [word for word in words if word not in PHRASE_STOPWORDS]

    if len(content_words) < 2:
        return False

    if any(word in STOPWORDS for word in words[1:-1]):
        return False

    return _phrase_has_signal(content_words)


def _is_useful_single_candidate(
    candidate: str,
    known_keywords: set[str],
    min_length: int,
) -> bool:
    normalized = _normalize_candidate(candidate)

    if len(normalized) < min_length:
        return normalized in STRONG_STANDALONE_SKILLS

    if (
        normalized in STOPWORDS
        or normalized in GENERIC_SINGLE_WORDS
        or normalized in NOISE_SINGLE_TERMS
    ):
        return False

    if normalized in DOMAIN_SKILL_KEYWORDS:
        return True

    if has_domain_term_pattern(candidate):
        return True

    if _is_known_candidate(candidate, known_keywords):
        return False

    if normalized in STRONG_STANDALONE_SKILLS:
        return True

    if normalized.isdigit():
        return False

    if normalized.endswith(("er", "en", "em", "es")) and len(normalized) < 8:
        return False

    return any(hint in normalized for hint in SKILL_HINTS)


def _candidate_sort_key(candidate: str):
    words = _normalize_candidate(candidate).split()
    signal_count = sum(
        1
        for word in words
        if word in MULTIWORD_SIGNALS or word in STRONG_STANDALONE_SKILLS
    )

    return (-signal_count, -len(words), candidate.lower())


def _remove_subphrase_noise(candidates: set[str]) -> set[str]:
    normalized_candidates = {
        candidate: _normalize_candidate(candidate)
        for candidate in candidates
    }
    cleaned = set(candidates)

    for candidate, normalized in normalized_candidates.items():
        words = normalized.split()

        if len(words) < 2 or normalized in PREFERRED_MULTIWORD_SKILLS:
            continue

        for other, other_normalized in normalized_candidates.items():
            if candidate == other:
                continue

            other_words = other_normalized.split()

            if len(other_words) <= len(words):
                continue

            for index in range(0, len(other_words) - len(words) + 1):
                if other_words[index : index + len(words)] == words:
                    cleaned.discard(candidate)
                    break

            if candidate not in cleaned:
                break

    return cleaned


def detect_unknown_skill_candidates(
    text: str,
    min_length: int = 5,
) -> list[str]:
    if not text:
        return []

    known_keywords = _known_keywords()
    token_lines = _tokenize_lines(text)
    candidates = set()

    for size in range(5, 1, -1):
        for tokens in token_lines:
            if len(tokens) < size:
                continue

            for index in range(0, len(tokens) - size + 1):
                candidate_tokens = _trim_candidate_tokens(
                    tokens[index : index + size]
                )

                if len(candidate_tokens) < 2:
                    continue

                candidate = _display_candidate(candidate_tokens)

                if _is_useful_multiword_candidate(candidate, known_keywords):
                    candidates.add(_canonical_phrase(candidate) or candidate)

    for tokens in token_lines:
        for token in tokens:
            if _is_useful_single_candidate(token, known_keywords, min_length):
                candidates.add(_canonical_phrase(token) or token)

    return sorted(_remove_subphrase_noise(candidates), key=_candidate_sort_key)


def debug_unknown_skill_candidates(text: str) -> dict:
    candidates = detect_unknown_skill_candidates(text)

    return {
        "count": len(candidates),
        "candidates": candidates,
    }
