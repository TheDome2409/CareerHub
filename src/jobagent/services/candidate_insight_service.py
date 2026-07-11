import re


INSIGHT_FIELDS = {
    "key_projects": [
        "careerhub",
        "projekt",
        "project",
        "produktentwicklung",
        "rollout",
        "migration",
        "implementierung",
        "implementation",
        "einfuehrung",
        "einfuehrte",
        "plattform",
        "platform",
        "tool",
        "mvp",
        "prototyping",
        "geschaeftsmodell",
        "geschaeftsmodelle",
    ],
    "key_achievements": [
        "erfolgreich",
        "umgesetzt",
        "realisiert",
        "verbessert",
        "reduziert",
        "optimiert",
        "automatisiert",
        "aufgebaut",
        "eingefuehrt",
        "verantwortet",
        "entscheidungsvorlagen",
        "wirtschaftlichkeitsbetrachtung",
        "wirtschaftlichkeitsbetrachtungen",
    ],
    "key_strengths": [
        "staerke",
        "schwerpunkt",
        "kompetenz",
        "erfahrung",
        "expertise",
        "kenntnisse",
        "business-it",
        "business it",
    ],
    "domain_experience": [
        "edi",
        "erp",
        "it-infrastruktur",
        "infrastruktur",
        "digitalisierung",
        "prozess",
        "consulting",
        "projektmanagement",
        "business-it",
        "business it",
        "geschaeftsmodell",
        "geschaeftsmodelle",
    ],
    "leadership_signals": [
        "fuehrung",
        "leitung",
        "lead",
        "teamleitung",
        "koordination",
        "verantwortung",
        "stakeholder",
        "entscheidungsvorlagen",
        "wirtschaftlichkeitsbetrachtung",
        "wirtschaftlichkeitsbetrachtungen",
    ],
    "technology_signals": [
        "python",
        "qwen",
        "ollama",
        "ki",
        "ai",
        "azure",
        "linux",
        "microsoft",
        "api",
        "edi",
        "erp",
        "sql",
        "automatisierung",
        "explainability",
        "mvp",
        "prototyping",
    ],
    "process_improvement_examples": [
        "prozessoptimierung",
        "prozess",
        "workflow",
        "automatisierung",
        "standardisierung",
        "verbesserung",
        "optimierung",
        "business-it",
        "business it",
        "wirtschaftlichkeitsbetrachtung",
        "wirtschaftlichkeitsbetrachtungen",
    ],
    "digitalization_examples": [
        "digitalisierung",
        "digitalization",
        "transformation",
        "careerhub",
        "ki",
        "ai",
        "automatisierung",
        "plattform",
        "produktentwicklung",
        "geschaeftsmodell",
        "geschaeftsmodelle",
    ],
}

FIELD_LABELS = {
    "key_projects": "Key Projects",
    "key_achievements": "Key Achievements",
    "key_strengths": "Key Strengths",
    "domain_experience": "Domain Experience",
    "leadership_signals": "Leadership Signals",
    "technology_signals": "Technology Signals",
    "process_improvement_examples": "Process Improvement Examples",
    "digitalization_examples": "Digitalization Examples",
}

PRIORITY_TERMS = [
    "careerhub",
    "produktentwicklung",
    "explainability",
    "business-it",
    "business it",
    "wirtschaftlichkeitsbetrachtung",
    "wirtschaftlichkeitsbetrachtungen",
    "entscheidungsvorlagen",
    "dienstleisterkoordination",
    "edi",
    "geschaeftsmodell",
    "geschaeftsmodelle",
    "geschäftsmodell",
    "geschäftsmodelle",
    "mvp",
    "prototyping",
]


def _normalize(value: str) -> str:
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


def _is_page_number(line: str) -> bool:
    return bool(
        re.fullmatch(
            r"(seite\s*)?\d{1,3}",
            line.strip().lower(),
        )
    )


def _is_repeated_header_footer(line: str, counts: dict[str, int]) -> bool:
    normalized = _normalize(
        line
    )

    if counts.get(normalized, 0) <= 1:
        return False

    header_markers = [
        "bewerbung",
        "gesamtmappe",
        "dominik kuehnel",
        "synatix",
        "seite",
    ]

    return len(line) <= 90 and any(
        marker in normalized
        for marker in header_markers
    )


def _should_join_lines(previous: str, current: str) -> bool:
    if not previous:
        return False

    if previous.endswith((".", "!", "?", ":")):
        return False

    if current.startswith(("•", "-", "–")):
        return False

    return True


def _fix_pdf_artifacts(text: str) -> str:
    replacements = {
        r"\bGESCHÄFTSMOD\s+ELLE\b": "GESCHÄFTSMODELLE",
        r"\bGeschäftsmod\s+elle\b": "Geschäftsmodelle",
        r"\bgeschaeftsmod\s+elle\b": "geschaeftsmodelle",
        r"\bBusiness\s*-\s*IT\b": "Business-IT",
        r"\bWirtschaftlichkeits\s+betrachtung(en)?\b": (
            "Wirtschaftlichkeitsbetrachtung\\1"
        ),
    }

    for pattern, replacement in replacements.items():
        text = re.sub(
            pattern,
            replacement,
            text,
            flags=re.IGNORECASE,
        )

    return text


def normalize_document_text(text: str) -> str:
    text = (text or "").replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )
    text = re.sub(
        r"(\w)-\n(\w)",
        r"\1\2",
        text,
    )
    raw_lines = [
        re.sub(
            r"\s+",
            " ",
            line.strip(),
        )
        for line in text.split("\n")
    ]
    counts = {}

    for line in raw_lines:
        normalized = _normalize(
            line
        )

        if normalized:
            counts[normalized] = counts.get(
                normalized,
                0,
            ) + 1

    paragraphs = []
    current = ""

    for line in raw_lines:
        if not line:
            if current:
                paragraphs.append(
                    current
                )
                current = ""
            continue

        if _is_page_number(line) or _is_repeated_header_footer(
            line,
            counts,
        ):
            continue

        if _should_join_lines(
            current,
            line,
        ):
            current = f"{current} {line}"
        else:
            if current:
                paragraphs.append(
                    current
                )

            current = line

    if current:
        paragraphs.append(
            current
        )

    normalized_text = "\n".join(
        paragraphs
    )
    normalized_text = _fix_pdf_artifacts(
        normalized_text
    )
    normalized_text = re.sub(
        r"[ \t]+",
        " ",
        normalized_text,
    )

    return re.sub(
        r"\n{3,}",
        "\n\n",
        normalized_text,
    ).strip()


def _candidate_sentences(text: str) -> list[str]:
    sentences = []

    for raw_line in (text or "").splitlines():
        line = re.sub(
            r"\s+",
            " ",
            raw_line.strip(),
        )

        if not line:
            continue

        parts = re.split(
            r"(?<=[.!?])\s+",
            line,
        )

        for part in parts:
            part = part.strip(" -\t")

            if len(part) < 12:
                continue

            sentences.append(
                part
            )

    return sentences


def _priority_match(sentence: str) -> re.Match[str] | None:
    best_match = None

    for term in PRIORITY_TERMS:
        pattern = re.escape(
            term
        ).replace(
            r"\-",
            r"\s*-\s*",
        )

        match = re.search(
            pattern,
            sentence,
            flags=re.IGNORECASE,
        )

        if match and (best_match is None or match.start() > best_match.start()):
            best_match = match

    return best_match


def _shorten(sentence: str, max_chars: int = 180) -> str:
    sentence = re.sub(
        r"\s+",
        " ",
        sentence.strip(),
    )

    if len(sentence) <= max_chars:
        return sentence

    priority_match = _priority_match(
        sentence
    )

    if priority_match:
        start = max(
            0,
            priority_match.start() - max_chars // 3,
        )
        end = min(
            len(sentence),
            start + max_chars - 3,
        )
        start = max(
            0,
            end - (max_chars - 3),
        )
        excerpt = sentence[start:end].strip()

        if start > 0:
            excerpt = "..." + excerpt

        if end < len(sentence):
            excerpt = excerpt.rstrip() + "..."

        return excerpt

    return sentence[: max_chars - 3].rstrip() + "..."


def _dedupe(items: list[str], limit: int = 5) -> list[str]:
    seen = set()
    result = []
    ranked_items = sorted(
        enumerate(items),
        key=lambda item: (
            -sum(
                1
                for term in PRIORITY_TERMS
                if _normalize(term) in _normalize(item[1])
            ),
            item[0],
        ),
    )

    for _index, item in ranked_items:
        normalized = _normalize(
            item
        )

        if not normalized or normalized in seen:
            continue

        seen.add(
            normalized
        )
        result.append(
            _shorten(
                item
            )
        )

        if len(result) >= limit:
            break

    return result


def extract_candidate_insights(text: str) -> dict[str, list[str]]:
    text = normalize_document_text(
        text
    )
    sentences = _candidate_sentences(
        text
    )
    insights = {
        field: []
        for field in INSIGHT_FIELDS
    }

    for sentence in sentences:
        normalized_sentence = _normalize(
            sentence
        )

        for field, patterns in INSIGHT_FIELDS.items():
            if any(
                _normalize(pattern) in normalized_sentence
                for pattern in patterns
            ):
                insights[field].append(
                    sentence
                )

    return {
        field: _dedupe(items)
        for field, items in insights.items()
    }


def format_candidate_insights(
    insights: dict[str, list[str]],
) -> str:
    sections = []

    for field, label in FIELD_LABELS.items():
        items = [
            item
            for item in insights.get(field, []) or []
            if str(item).strip()
        ]

        if not items:
            continue

        sections.append(
            label + ":\n" + "\n".join(f"- {item}" for item in items)
        )

    if not sections:
        return "Candidate Insights:\n- Keine strukturierten Candidate Insights erkannt."

    return "Candidate Insights:\n\n" + "\n\n".join(
        sections
    )
