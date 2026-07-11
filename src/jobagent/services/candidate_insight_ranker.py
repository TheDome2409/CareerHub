import re
from dataclasses import dataclass
from typing import Any

from jobagent.services.export_text_service import normalize_export_text


@dataclass
class CandidateInsightView:
    title: str
    description: str
    priority_score: int


FIELD_WEIGHTS = {
    "key_projects": 35,
    "key_achievements": 32,
    "leadership_signals": 28,
    "digitalization_examples": 26,
    "process_improvement_examples": 24,
    "domain_experience": 18,
    "key_strengths": 16,
    "technology_signals": 4,
}

TERM_WEIGHTS = {
    "careerhub": 70,
    "produktentwicklung": 35,
    "product development": 35,
    "explainability": 35,
    "business it": 35,
    "business-it": 35,
    "digitalisierung": 30,
    "digitalization": 30,
    "geschaeftsmodell": 30,
    "geschaeftsmodelle": 30,
    "geschaftsmodell": 30,
    "geschaftsmodelle": 30,
    "mvp": 30,
    "prototyping": 30,
    "prototyp": 28,
    "ki": 24,
    "ai": 24,
    "llm": 24,
    "transformation": 22,
    "prozessoptimierung": 22,
    "process improvement": 22,
    "venture": 22,
    "company building": 22,
    "venture building": 22,
    "edi": 14,
    "dienstleisterkoordination": 14,
    "infrastruktur": 10,
    "entscheidungsvorlagen": 34,
    "wirtschaftlichkeitsbetrachtung": 34,
    "wirtschaftlichkeitsbetrachtungen": 34,
    "verantwortung": 28,
    "koordination": 22,
    "stakeholder": 20,
}

TARGET_BOOST_TERMS = [
    "produktentwicklung",
    "product development",
    "digitalisierung",
    "digitalization",
    "geschaeftsmodell",
    "geschaeftsmodelle",
    "geschaftsmodell",
    "geschaftsmodelle",
    "venture",
    "company building",
    "venture building",
    "ki",
    "ai",
    "llm",
    "prototyping",
    "mvp",
    "prozessoptimierung",
    "process improvement",
    "business it",
    "business-it",
    "explainability",
]

TECHNICAL_FEATURE_TERMS = [
    "skill score",
    "competency score",
    "gesamtbewertung",
    "ranking",
    "canonicalization",
    "unknown skill review",
    "unknown skills",
    "pipeline",
    "import",
    "export",
    "csv import",
    "csv export",
    "review queue",
    "score result",
    "scoring komponenten",
    "matching score",
]

PERSONAL_EVIDENCE_TERMS = [
    "entwickle",
    "entwicklung",
    "projekt",
    "projektmanagement",
    "umgesetzt",
    "aufgebaut",
    "eingefuehrt",
    "verantwortet",
    "verantwortung",
    "koordination",
    "entscheidungsvorlagen",
    "wirtschaftlichkeitsbetrachtung",
    "business it",
    "business-it",
    "schnittstelle",
    "fachbereich",
    "stakeholder",
    "produktentwicklung",
    "digitalisierung",
]

GENERIC_LOW_VALUE_TERMS = [
    "generische it dokumentation",
    "ticketerfassung",
    "allgemeine it kenntnisse",
    "microsoft windows",
    "dokumentation",
]


def _normalize(value: Any) -> str:
    value = str(value or "").strip().lower()
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "Ã¤": "ae",
        "Ã¶": "oe",
        "Ã¼": "ue",
        "ÃŸ": "ss",
        "Ã„": "ae",
        "Ã–": "oe",
        "Ãœ": "ue",
    }

    for source, target in replacements.items():
        value = value.replace(
            source,
            target,
        )

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


def _contains(normalized_text: str, term: str) -> bool:
    return _normalize(term) in normalized_text


def _technical_feature_hits(normalized_text: str) -> list[str]:
    return [
        term
        for term in TECHNICAL_FEATURE_TERMS
        if _contains(normalized_text, term)
    ]


def _personal_evidence_hits(normalized_text: str) -> list[str]:
    return [
        term
        for term in PERSONAL_EVIDENCE_TERMS
        if _contains(normalized_text, term)
    ]


def _is_low_value_technical_feature(
    normalized_text: str,
    field: str,
) -> bool:
    technical_hits = _technical_feature_hits(
        normalized_text
    )

    if not technical_hits:
        return False

    personal_hits = _personal_evidence_hits(
        normalized_text
    )

    if len(technical_hits) >= 2 and len(personal_hits) <= 1:
        return True

    return field == "technology_signals" and len(personal_hits) == 0


def _is_generic_low_value_insight(normalized_text: str) -> bool:
    generic_hits = [
        term
        for term in GENERIC_LOW_VALUE_TERMS
        if _contains(normalized_text, term)
    ]

    if not generic_hits:
        return False

    return len(_personal_evidence_hits(normalized_text)) == 0


def _company_target_text(
    company_match,
    company_match_report: str = "",
) -> str:
    if not company_match:
        return company_match_report or ""

    company = getattr(
        company_match,
        "company",
        None,
    )
    parts = [
        company_match_report or "",
        " ".join(getattr(company_match, "reasons", []) or []),
        " ".join(getattr(company_match, "risk_flags", []) or []),
        getattr(company_match, "application_recommendation", "") or "",
    ]

    if company:
        parts.extend(
            [
                getattr(company, "name", "") or "",
                getattr(company, "description", "") or "",
                " ".join(getattr(company, "industries", []) or []),
                " ".join(getattr(company, "focus_areas", []) or []),
                " ".join(getattr(company, "possible_use_cases", []) or []),
                " ".join(getattr(company, "detected_skills", []) or []),
                " ".join(getattr(company, "detected_competencies", []) or []),
                " ".join(
                    getattr(company, "qualification_requirements", []) or []
                ),
            ]
        )

    return "\n".join(
        part
        for part in parts
        if str(part).strip()
    )


def _score_insight(
    field: str,
    insight: str,
    target_text: str,
    company_name: str = "",
) -> tuple[int, list[str]]:
    normalized_insight = _normalize(
        insight
    )
    normalized_target = _normalize(
        target_text
    )
    score = FIELD_WEIGHTS.get(
        field,
        3,
    )
    reasons = [
        f"field:{field}"
    ]
    technical_hits = _technical_feature_hits(
        normalized_insight
    )

    for term, weight in TERM_WEIGHTS.items():
        if _contains(
            normalized_insight,
            term,
        ):
            score += weight
            reasons.append(
                term
            )

    if technical_hits:
        penalty = 35 + 18 * len(technical_hits)
        score -= penalty
        reasons.append(
            "technical-product-feature"
        )

    for term in TARGET_BOOST_TERMS:
        if _contains(normalized_insight, term) and _contains(
            normalized_target,
            term,
        ):
            score += 18
            reasons.append(
                f"target:{term}"
            )

    normalized_company_name = _normalize(
        company_name
    )
    candidate_markers = [
        "careerhub",
        "projekt",
        "entwickle",
        "erfahrung",
        "umgesetzt",
        "koordination",
        "edi",
        "mvp",
        "prototyp",
    ]

    if (
        normalized_company_name
        and normalized_company_name in normalized_insight
        and not any(marker in normalized_insight for marker in candidate_markers)
    ):
        score -= 45
        reasons.append(
            "company-context-penalty"
        )

    return score, reasons


def rank_candidate_insights(
    insights: dict[str, list[str]],
    company_match=None,
    company_match_report: str = "",
    limit: int = 5,
) -> list[dict[str, object]]:
    target_text = _company_target_text(
        company_match,
        company_match_report,
    )
    company = getattr(
        company_match,
        "company",
        None,
    )
    company_name = getattr(
        company,
        "name",
        "",
    )
    ranked = []
    seen = set()
    order = 0

    for field, items in (insights or {}).items():
        for insight in items or []:
            normalized = _normalize(
                insight
            )

            if not normalized or normalized in seen:
                continue

            if _is_low_value_technical_feature(
                normalized,
                field,
            ) or _is_generic_low_value_insight(
                normalized,
            ):
                continue

            seen.add(
                normalized
            )
            score, reasons = _score_insight(
                field,
                insight,
                target_text,
                company_name,
            )
            ranked.append(
                {
                    "insight": insight,
                    "field": field,
                    "score": score,
                    "reasons": reasons,
                    "order": order,
                }
            )
            order += 1

    ranked.sort(
        key=lambda item: (
            -int(item["score"]),
            int(item["order"]),
        )
    )

    return ranked[:limit]


def format_ranked_candidate_insights(
    ranked_insights: list[dict[str, object]],
) -> str:
    if not ranked_insights:
        return "Top Candidate Insights:\n- Keine priorisierten Candidate Insights erkannt."

    lines = [
        "Top Candidate Insights:"
    ]

    for index, item in enumerate(
        ranked_insights,
        start=1,
    ):
        lines.append(
            f"{index}. {item.get('insight', '')}"
        )

    return "\n".join(
        lines
    )


def _clean_fragment(value: str) -> str:
    value = re.sub(
        r"^\s*(\d+\.\s*)?",
        "",
        value or "",
    )
    value = value.replace(
        "...",
        " ",
    )
    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip(" -:;")

    return normalize_export_text(
        value
    )


def _has_any(normalized: str, terms: list[str]) -> bool:
    return any(
        _normalize(term) in normalized
        for term in terms
    )


def _title_for_insight(normalized: str, raw: str) -> str:
    if "careerhub" in normalized:
        return "CareerHub - KI-gestützte Produktentwicklung"

    if _has_any(
        normalized,
        [
            "business it",
            "entscheidungsvorlagen",
            "wirtschaftlichkeitsbetrachtung",
        ],
    ):
        return "Business-IT-Schnittstelle und Entscheidungsgrundlagen"

    if _has_any(
        normalized,
        [
            "produktentwicklung",
            "geschaeftsmodell",
            "geschaeftsmodelle",
            "venture",
        ],
    ):
        return "Produktentwicklung und digitale Geschäftsmodelle"

    if _has_any(
        normalized,
        [
            "mvp",
            "prototyp",
            "prototyping",
        ],
    ):
        return "MVP und Prototyping"

    if "edi" in normalized:
        return "EDI und Prozessdigitalisierung"

    if _has_any(
        normalized,
        [
            "infrastruktur",
            "endpoint",
            "server",
            "mde",
            "mdm",
        ],
    ):
        return "IT-Infrastruktur und Umsetzung"

    words = raw.split()

    return " ".join(words[:7]).rstrip(".,;:")


def _description_for_insight(normalized: str, raw: str) -> str:
    if "careerhub" in normalized:
        details = []

        if "ocr" in normalized:
            details.append("OCR")

        if _has_any(normalized, ["llm", "qwen"]):
            details.append("LLM-Integration")

        if "ranking" in normalized:
            details.append("Ranking")

        if "scoring" in normalized:
            details.append("Scoring")

        if "explainability" in normalized:
            details.append("Explainability")

        detail_text = ", ".join(details)

        if detail_text:
            return (
                "Eigenständige Entwicklung einer Plattform zur Analyse "
                "von Stellenanzeigen und Bewerbungsprofilen mit "
                f"{detail_text}."
            )

        return (
            "Eigenständige Entwicklung von CareerHub als KI-gestütztes "
            "Produkt- und Lernprojekt im Karriere- und Matching-Kontext."
        )

    if _has_any(
        normalized,
        [
            "business it",
            "entscheidungsvorlagen",
            "wirtschaftlichkeitsbetrachtung",
        ],
    ):
        return (
            "Verbindung von technischer Analyse, Fachbereichskommunikation "
            "und entscheidungsfähigen Unterlagen für Management- oder "
            "Geschäftsführungskontexte."
        )

    if _has_any(
        normalized,
        [
            "produktentwicklung",
            "geschaeftsmodell",
            "geschaeftsmodelle",
            "venture",
        ],
    ):
        return (
            "Erfahrung an der Schnittstelle von Technik, Produktdenken "
            "und digitalen Geschäftsmodellen."
        )

    if _has_any(
        normalized,
        [
            "mvp",
            "prototyp",
            "prototyping",
        ],
    ):
        return (
            "Pragmatische Umsetzung von Ideen in testbare Prototypen "
            "und MVP-nahe Lösungen."
        )

    if "edi" in normalized:
        return (
            "Erfahrung mit EDI-nahen Prozessen, Dokumentation und "
            "prozessbezogener Digitalisierung."
        )

    if _has_any(
        normalized,
        [
            "infrastruktur",
            "endpoint",
            "server",
            "mde",
            "mdm",
        ],
    ):
        return (
            "Hands-on-Erfahrung in technischer Umsetzung, Koordination "
            "und stabiler IT-Infrastrukturarbeit."
        )

    return normalize_export_text(
        raw.rstrip(".") + "."
    )


def build_candidate_insight_views(
    ranked_insights: list[dict[str, object]],
) -> list[CandidateInsightView]:
    views = []
    seen_titles = set()

    for item in ranked_insights or []:
        raw = _clean_fragment(
            str(item.get("insight", ""))
        )

        if not raw:
            continue

        normalized = _normalize(
            raw
        )
        title = _title_for_insight(
            normalized,
            raw,
        )
        title = normalize_export_text(
            title
        )

        if title in seen_titles:
            continue

        seen_titles.add(
            title
        )
        views.append(
            CandidateInsightView(
                title=title,
                description=_description_for_insight(
                    normalized,
                    raw,
                ),
                priority_score=int(
                    item.get("score", 0)
                ),
            )
        )

    return views


def format_candidate_insight_views(
    views: list[CandidateInsightView],
) -> str:
    if not views:
        return ""

    lines = []

    for view in views:
        lines.append(
            f"{view.title}\n{view.description}"
        )

    return "\n\n".join(
        lines
    )
