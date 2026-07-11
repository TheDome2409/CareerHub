import re
import unicodedata

from jobagent.models.tag_labels import label_tag


COMMON_MOJIBAKE_REPLACEMENTS = {
    "Ã„": "Ä",
    "Ã–": "Ö",
    "Ãœ": "Ü",
    "Ã¤": "ä",
    "Ã¶": "ö",
    "Ã¼": "ü",
    "ÃŸ": "ß",
    "Ã©": "é",
    "Ã¨": "è",
    "Ã¡": "á",
    "Ã³": "ó",
    "ÃƒÂ„": "Ä",
    "ÃƒÂ–": "Ö",
    "ÃƒÅ“": "Ü",
    "ÃƒÂ¤": "ä",
    "ÃƒÂ¶": "ö",
    "ÃƒÂ¼": "ü",
    "ÃƒÅ¸": "ß",
    "Ã¢â‚¬â€œ": "-",
    "Ã¢â‚¬â€": "-",
    "Ã¢â‚¬Å¾": '"',
    "Ã¢â‚¬Å“": '"',
    "Ã¢â‚¬Â": '"',
    "Ã¢â‚¬Ëœ": "'",
    "Ã¢â‚¬â„¢": "'",
    "Ã‚Â·": "-",
    "Ã‚": "",
}

TYPOGRAPHIC_REPLACEMENTS = {
    "\u00a0": " ",
    "\u202f": " ",
    "\u2007": " ",
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u2026": "...",
}

EMOJI_MOJIBAKE_PATTERN = re.compile(
    r"(?:Ã°Å¸|Ã¢Å“|Ã¢Ëœ|Ã¢Å¡|Ã¯Â¸|Ã°ÂŸ|ðŸ)[^\sA-Za-zÄÖÜäöüß/.-]*"
)


def repair_common_mojibake(text: str | None) -> str:
    value = str(text or "")

    for source, target in COMMON_MOJIBAKE_REPLACEMENTS.items():
        value = value.replace(
            source,
            target,
        )

    return value


def normalize_export_text(text: str | None) -> str:
    if text is None:
        return ""

    value = unicodedata.normalize(
        "NFC",
        str(text),
    )
    value = repair_common_mojibake(
        value
    )

    for source, target in TYPOGRAPHIC_REPLACEMENTS.items():
        value = value.replace(
            source,
            target,
        )

    value = EMOJI_MOJIBAKE_PATTERN.sub(
        "",
        value,
    )
    value = "".join(
        char
        for char in value
        if unicodedata.category(char) != "So"
    )
    value = re.sub(
        r"[\u200d\ufe0f]",
        "",
        value,
    )
    value = re.sub(
        r"[ \t]+",
        " ",
        value,
    )
    value = re.sub(
        r"\n[ \t]+",
        "\n",
        value,
    )
    value = re.sub(
        r"\n{3,}",
        "\n\n",
        value,
    )

    return value.strip()


def normalize_export_items(items: list[str] | None) -> list[str]:
    return [
        normalized
        for normalized in (
            normalize_export_text(item)
            for item in items or []
        )
        if normalized
    ]


def safe_export_label(label: str | None) -> str:
    value = normalize_export_text(
        label
    )
    value = re.sub(
        r"^[^\wÄÖÜäöüß]+",
        "",
        value,
    )
    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    return value


def export_label_tag(tag: str) -> str:
    label = safe_export_label(
        label_tag(tag)
    )

    return label or str(tag)
