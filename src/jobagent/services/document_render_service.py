from html import escape

from jobagent.models.document_model import (
    Document,
    DocumentBlock,
    DocumentSection,
)
from jobagent.ui.branding import APP_NAME, logo_data_uri


def _text(value) -> str:
    return str(value or "").strip()


def _has_content(block: DocumentBlock) -> bool:
    return bool(
        _text(block.content)
        or block.items
        or block.metadata
    )


def _section_has_content(section: DocumentSection) -> bool:
    return any(
        _has_content(block)
        for block in section.blocks
    )


def _paragraph_html(block: DocumentBlock) -> str:
    content = escape(
        _text(block.content)
    ).replace(
        "\n",
        "<br>",
    )

    return f'<p class="document-paragraph">{content}</p>'


def _bullet_list_html(block: DocumentBlock) -> str:
    items = [
        f"<li>{escape(_text(item))}</li>"
        for item in block.items
        if _text(item)
    ]

    return f'<ul class="document-list">{"".join(items)}</ul>'


def _key_value_table_html(block: DocumentBlock) -> str:
    values = block.content if isinstance(block.content, dict) else {}

    rows = [
        (
            "<tr>"
            f"<th>{escape(_text(key))}</th>"
            f"<td>{escape(_text(value))}</td>"
            "</tr>"
        )
        for key, value in values.items()
        if _text(key) and _text(value)
    ]

    return f'<table class="document-table">{"".join(rows)}</table>'


def _card_list_html(block: DocumentBlock) -> str:
    cards = []

    for item in block.items:
        if isinstance(item, dict):
            title = _text(item.get("title"))
            description = _text(item.get("description") or item.get("content"))
        else:
            title = ""
            description = _text(item)

        if not title and not description:
            continue

        cards.append(
            (
                '<article class="document-card">'
                f"{f'<h3>{escape(title)}</h3>' if title else ''}"
                f"<p>{escape(description)}</p>"
                "</article>"
            )
        )

    return f'<div class="document-card-list">{"".join(cards)}</div>'


def _attachment_overview_html(block: DocumentBlock) -> str:
    items = []

    for item in block.items:
        if isinstance(item, dict):
            title = _text(item.get("title") or item.get("name"))
            description = _text(item.get("description") or item.get("reason"))
        else:
            title = _text(item)
            description = ""

        if not title:
            continue

        items.append(
            (
                '<li class="document-attachment">'
                f"<strong>{escape(title)}</strong>"
                f"{f'<br><span>{escape(description)}</span>' if description else ''}"
                "</li>"
            )
        )

    return f'<ol class="document-attachments">{"".join(items)}</ol>'


def _skill_grid_html(block: DocumentBlock) -> str:
    items = [
        f'<span class="document-skill">{escape(_text(item))}</span>'
        for item in block.items
        if _text(item)
    ]

    return f'<div class="document-skill-grid">{"".join(items)}</div>'


def _block_body_html(block: DocumentBlock) -> str:
    if block.kind == "paragraph":
        return _paragraph_html(block)

    if block.kind == "bullet_list":
        return _bullet_list_html(block)

    if block.kind == "key_value_table":
        return _key_value_table_html(block)

    if block.kind == "card_list":
        return _card_list_html(block)

    if block.kind == "skill_grid":
        return _skill_grid_html(block)

    if block.kind == "attachment_overview":
        return _attachment_overview_html(block)

    return _paragraph_html(block)


def _block_html(block: DocumentBlock) -> str:
    if not _has_content(block):
        return ""

    title = (
        f"<h3>{escape(_text(block.title))}</h3>"
        if _text(block.title)
        else ""
    )

    return (
        f'<div class="document-block document-block-{escape(block.kind)}">'
        f"{title}{_block_body_html(block)}</div>"
    )


def _section_html(
    section: DocumentSection,
    rendered_attachment_overview: bool,
) -> tuple[str, bool]:
    if not _section_has_content(section):
        return "", rendered_attachment_overview

    blocks = []

    for block in section.blocks:
        if block.kind == "attachment_overview":
            if rendered_attachment_overview:
                continue

            rendered_attachment_overview = True

        block_html = _block_html(block)

        if block_html:
            blocks.append(block_html)

    if not blocks:
        return "", rendered_attachment_overview

    classes = [
        "document-section",
        f"document-section-{section.kind}",
    ]

    if section.page_break_before:
        classes.append("document-page-break-before")

    if section.keep_together:
        classes.append("document-keep-together")

    html = (
        f'<section class="{" ".join(classes)}">'
        f"<h2>{escape(section.title)}</h2>"
        f"{''.join(blocks)}</section>"
    )

    return html, rendered_attachment_overview


def _footer_html(document: Document) -> str:
    footer_note = _text(
        document.metadata.get("footer_note")
        or f"Erstellt mit {APP_NAME}"
    )

    return f'<footer class="document-footer">{escape(footer_note)}</footer>'


def render_document_to_html(document: Document) -> str:
    rendered_attachment_overview = False
    sections = []

    for section in document.sections:
        section_html, rendered_attachment_overview = _section_html(
            section,
            rendered_attachment_overview,
        )

        if section_html:
            sections.append(section_html)

    subtitle_html = (
        f'<p class="document-subtitle">{escape(_text(document.subtitle))}</p>'
        if _text(document.subtitle)
        else ""
    )

    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{escape(document.title)}</title>
<style>
@page {{
    size: A4;
    margin: 18mm 16mm;
}}

body {{
    margin: 0;
    color: #111827;
    background: #f3f4f6;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 11pt;
    line-height: 1.48;
}}

.document-page {{
    width: 210mm;
    min-height: 297mm;
    margin: 18mm auto;
    padding: 18mm 20mm;
    box-sizing: border-box;
    background: #ffffff;
}}

.document-header {{
    border-bottom: 2px solid #2563eb;
    margin-bottom: 18px;
    padding-bottom: 10px;
}}

.document-brand {{
    display: inline-flex;
    align-items: center;
    gap: 10px;
    font-size: 24px;
    font-weight: bold;
}}

.document-brand img {{
    width: 30px;
    height: 30px;
}}

.document-title {{
    margin: 22px 0 4px;
    font-size: 28px;
    line-height: 1.15;
}}

.document-subtitle {{
    margin: 0;
    color: #6b7280;
}}

.document-section {{
    margin: 0 0 20px;
}}

.document-page-break-before {{
    page-break-before: always;
    break-before: page;
}}

.document-keep-together,
.document-card,
.document-block-key_value_table,
.document-block-attachment_overview {{
    page-break-inside: avoid;
    break-inside: avoid;
}}

.document-section h2 {{
    color: #2563eb;
    font-size: 18px;
    margin: 18px 0 10px;
    page-break-after: avoid;
    break-after: avoid;
}}

.document-block {{
    margin: 0 0 14px;
}}

.document-block h3 {{
    margin: 0 0 6px;
    font-size: 14px;
}}

.document-list,
.document-attachments {{
    margin: 0;
    padding-left: 20px;
}}

.document-list li,
.document-attachment {{
    margin-bottom: 8px;
}}

.document-table {{
    width: 100%;
    border-collapse: collapse;
}}

.document-table th {{
    width: 34%;
    text-align: left;
    color: #374151;
    padding: 6px 8px 6px 0;
}}

.document-table td {{
    padding: 6px 0;
}}

.document-card-list {{
    display: grid;
    gap: 10px;
}}

.document-card {{
    border: 1px solid #dbeafe;
    border-left: 4px solid #2563eb;
    border-radius: 8px;
    background: #f8fafc;
    padding: 12px 14px;
}}

.document-card p {{
    margin: 0;
}}

.document-skill-grid {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}}

.document-skill {{
    border: 1px solid #dbeafe;
    border-radius: 999px;
    padding: 4px 9px;
    background: #eff6ff;
}}

.document-footer {{
    border-top: 1px solid #e5e7eb;
    margin-top: 18px;
    padding-top: 8px;
    color: #6b7280;
    font-size: 10pt;
}}

@media print {{
    body {{
        background: white;
    }}

    .document-page {{
        width: auto;
        min-height: auto;
        margin: 0;
        padding: 0;
    }}
}}
</style>
</head>
<body>
<main class="document-page">
    <header class="document-header">
        <span class="document-brand">
            <img src="{logo_data_uri()}" alt="{APP_NAME} Logo">
            {escape(APP_NAME)}
        </span>
        <h1 class="document-title">{escape(document.title)}</h1>
        {subtitle_html}
    </header>
    {''.join(sections)}
    {_footer_html(document)}
</main>
</body>
</html>
"""
