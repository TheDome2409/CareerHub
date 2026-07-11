import re


ALLOWED_DOMAINS = {
    "it",
    "finance",
    "healthcare",
    "education",
    "public_service",
    "legal",
    "craft",
    "general_business",
    "unknown",
}

DOMAIN_TERM_SUFFIXES = {
    "beratung",
    "bescheid",
    "bescheide",
    "dokumentation",
    "fachverfahren",
    "fuehrung",
    "führung",
    "gesetz",
    "management",
    "messung",
    "ordnung",
    "planung",
    "pruefung",
    "prüfung",
    "recht",
    "schau",
    "schutz",
    "sicherung",
    "technik",
    "verfahren",
}

DOMAIN_KEYWORDS = {
    "finance": {
        "anlagenbuchhaltung",
        "buchhaltung",
        "datev",
        "debitorenbuchhaltung",
        "kontenabstimmung",
        "kreditorenbuchhaltung",
        "sap fi",
        "umsatzsteuervoranmeldung",
    },
    "healthcare": {
        "basale stimulation",
        "entlassungsmanagement",
        "kinaesthetik",
        "kinästhetik",
        "krankenhausinformationssystem",
        "krinko",
        "wundexperte icw",
        "wundversorgung",
    },
    "education": {
        "entwicklungsgespraeche",
        "entwicklungsgespräche",
        "inklusion",
        "inklusionspaedagogik",
        "inklusionspädagogik",
        "kinderschutz",
        "marte meo",
        "situationsansatz",
        "sprachfoerderung",
        "sprachförderung",
    },
    "it": {
        "azure landing zone",
        "conditional access policies",
        "gitops",
        "infrastructure as code",
        "platform engineering",
        "privileged access management",
        "zero trust",
    },
    "general_business": {
        "change management",
        "lieferantensteuerung",
        "prozessmanagement",
        "stakeholdermanagement",
        "workshopmoderation",
    },
    "public_service": {
        "fachverfahren",
        "verwaltungsbescheid",
        "verwaltungsbescheide",
        "widerspruchsverfahren",
    },
    "legal": {
        "datenschutzrecht",
        "kommunalrecht",
        "ordnungsrecht",
        "vergaberecht",
        "verwaltungsrecht",
    },
    "craft": {
        "abgasmessung",
        "abgaswegepruefung",
        "abgaswegeprüfung",
        "brandschutz",
        "feuerstaettenschau",
        "feuerstättenschau",
        "gebaeudeenergiegesetz",
        "gebäudeenergiegesetz",
        "immissionsschutz",
        "kehrbuchfuehrung",
        "kehrbuchführung",
        "schornsteintechnik",
    },
}


def normalize_domain_text(value: str) -> str:
    value = (value or "").strip().lower()
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
        "ÃƒÆ’Ã‚Â¤": "ae",
        "ÃƒÆ’Ã‚Â¶": "oe",
        "ÃƒÆ’Ã‚Â¼": "ue",
        "ÃƒÆ’Ã…Â¸": "ss",
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


def domain_keywords() -> set[str]:
    keywords = set()

    for values in DOMAIN_KEYWORDS.values():
        for value in values:
            keywords.add(
                normalize_domain_text(value)
            )

    return keywords


def domain_term_suffixes() -> set[str]:
    return {
        normalize_domain_text(value)
        for value in DOMAIN_TERM_SUFFIXES
    }


def has_domain_term_pattern(candidate: str) -> bool:
    normalized_candidate = normalize_domain_text(candidate)

    if len(normalized_candidate) < 8:
        return False

    words = normalized_candidate.split()

    if len(words) > 3:
        return False

    compact = "".join(words)

    return any(
        compact.endswith(suffix)
        for suffix in domain_term_suffixes()
    )


def detect_candidate_domain(
    candidate: str,
    context_text: str = "",
) -> str:
    normalized_candidate = normalize_domain_text(candidate)
    normalized_context = normalize_domain_text(context_text)

    for domain, keywords in DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            normalized_keyword = normalize_domain_text(
                keyword
            )

            if normalized_keyword and normalized_keyword in normalized_candidate:
                return domain

    compact = normalized_candidate.replace(" ", "")

    if compact.endswith("recht"):
        return "legal"

    if compact.endswith(
        (
            "bescheid",
            "bescheide",
            "fachverfahren",
            "verfahren",
        )
    ):
        return "public_service"

    if (
        compact.endswith(
            (
                "messung",
                "pruefung",
                "schau",
                "schutz",
                "technik",
            )
        )
        or "kehrbuch" in compact
    ):
        return "craft"

    if normalized_context:
        for domain, keywords in DOMAIN_KEYWORDS.items():
            for keyword in keywords:
                normalized_keyword = normalize_domain_text(
                    keyword
                )

                if (
                    normalized_keyword
                    and normalized_keyword in normalized_context
                    and normalized_keyword in normalized_candidate
                ):
                    return domain

    return "unknown"


def normalize_candidate_domain(value: str | None) -> str:
    domain = normalize_domain_text(value or "")

    if domain in ALLOWED_DOMAINS:
        return domain

    return "unknown"
