from datetime import date
from html import escape, unescape
import re
from urllib.parse import quote

from jobagent.services.attachment_preview_service import (
    pdf_preview_jpeg_data_uri,
)
from jobagent.services.export_text_service import (
    export_label_tag,
    normalize_export_text,
)
from jobagent.ui.branding import APP_NAME, logo_data_uri


def _company_display(company: str | None) -> str:
    if company:
        return company

    return "Arbeitgeber in der Stellenanzeige nicht eindeutig genannt"


def _attachment_preview_data_uri(item: dict) -> str | None:
    file_bytes = item.get("bytes")
    name = str(
        item.get("name")
        or item.get("archive_name")
        or ""
    ).lower()

    if not file_bytes:
        return None

    if not (
        name.endswith(".pdf")
        or bytes(file_bytes).startswith(b"%PDF")
    ):
        return None

    return pdf_preview_jpeg_data_uri(
        bytes(file_bytes)
    )


def _has_resume_attachment(attachments: list[dict]) -> bool:
    return any(
        item.get("kind") == "resume"
        for item in attachments
    )


def _compact_text(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        value or "",
    ).strip()


def attachment_display_title(item: dict, index: int = 1) -> str:
    name = str(
        item.get("name")
        or item.get("archive_name")
        or ""
    )
    reason = str(
        item.get("reason")
        or ""
    )
    compact = re.sub(
        r"[^a-z0-9äöüß]+",
        " ",
        f"{name} {reason}".lower(),
    )

    known_titles = [
        (
            ["lebenslauf", "curriculum vitae"],
            "Lebenslauf",
        ),
        (
            ["careerhub", "architektur"],
            "CareerHub-Architektur / Status / Mehrwert",
        ),
        (
            ["careerhub", "status"],
            "CareerHub-Architektur / Status / Mehrwert",
        ),
        (
            ["careerhub", "mehrwert"],
            "CareerHub-Architektur / Status / Mehrwert",
        ),
        (
            ["careerhub"],
            "CareerHub-Projektvorstellung",
        ),
        (
            ["zwischenzeugnis", "example", "foods"],
            "Zwischenzeugnis Example Foods Gebäck GmbH",
        ),
        (
            ["ausbildungszeugnis", "example", "training"],
            "Ausbildungszeugnis Example Training GmbH",
        ),
        (
            ["ihk", "fachinformatiker", "systemintegration"],
            "IHK Prüfungszeugnis Fachinformatiker Systemintegration",
        ),
        (
            ["aevo"],
            "AEVO / IHK-Ausbilder",
        ),
        (
            ["ausbilder"],
            "AEVO / IHK-Ausbilder",
        ),
        (
            ["anlagenübersicht"],
            "Anlagenübersicht",
        ),
        (
            ["anlagenuebersicht"],
            "Anlagenübersicht",
        ),
    ]

    for terms, title in known_titles:
        if all(
            term in compact
            for term in terms
        ):
            return normalize_export_text(title)

    if "zeugnis" in compact:
        return "Zeugnis / Nachweis"

    if "zertifikat" in compact or "certificate" in compact:
        return "Zertifikat"

    if "projekt" in compact:
        return "Projektunterlage"

    return f"Anlage {index}"


def _attachment_original_note(name: str, display_title: str) -> str:
    name = _compact_text(name)

    if not name or name == display_title:
        return ""

    if re.search(
        r"anlage-seite-\d+\.pdf$",
        name,
        flags=re.IGNORECASE,
    ):
        return ""

    return (
        '<span class="attachment-original">'
        f"Originaldatei: {escape(normalize_export_text(name))}"
        "</span>"
    )


def _is_curated_attachment_title(title: str) -> bool:
    normalized = _compact_text(
        normalize_export_text(title)
    ).lower()

    if not normalized:
        return False

    generic_titles = {
        "anlage",
        "zeugnis / nachweis",
        "zertifikat",
        "projektunterlage",
    }

    if normalized in generic_titles:
        return False

    if re.fullmatch(
        r"anlage \d+",
        normalized,
    ):
        return False

    return True


def _is_attachment_overview_title(title: str) -> bool:
    normalized = _compact_text(
        normalize_export_text(title)
    ).lower()

    return normalized in {
        "anlagenübersicht",
        "anlagenuebersicht",
    }


def _is_attachment_overview_item(item: dict) -> bool:
    normalized = _compact_text(
        normalize_export_text(
            " ".join(
                [
                    str(item.get("name") or ""),
                    str(item.get("archive_name") or ""),
                    str(item.get("reason") or ""),
                ]
            )
        )
    ).lower()

    return (
        "anlagen" in normalized
        and (
            "übersicht" in normalized
            or "uebersicht" in normalized
            or "bersicht" in normalized
        )
    )


def _attachment_overview_reason(reason: str) -> str:
    reason = normalize_export_text(
        reason or ""
    )
    reason = re.sub(
        r"\s*Extrahiert aus .+?, Seite \d+\.?\s*$",
        "",
        reason,
        flags=re.IGNORECASE,
    ).strip()

    return reason or "Relevanter Nachweis"


def _insight_cards_html(top_candidate_insights: str) -> str:
    blocks = [
        block.strip()
        for block in (top_candidate_insights or "").split("\n\n")
        if block.strip()
    ]
    cards = []

    for block in blocks:
        lines = [
            line.strip()
            for line in block.splitlines()
            if line.strip()
        ]

        if not lines:
            continue

        title = normalize_export_text(
            lines[0].strip(" -:")
        )
        description = normalize_export_text(
            " ".join(lines[1:]).strip()
        )

        if not description:
            description = title

        if "..." in title or "..." in description:
            continue

        cards.append(
            """
    <div class="insight-card">
        <div>
            <h3>{title}</h3>
            <p>{description}</p>
        </div>
    </div>
""".format(
                title=escape(title),
                description=escape(description),
            )
        )

    return "\n".join(
        cards
    )


def generate_application_html(
    cover_letter: str,
    profile_summary: str,
    profile_tags: list[str],
    job_title: str,
    company: str | None,
    matched_tags: list[str] | None = None,
    missing_tags: list[str] | None = None,
    job_required_tags: list[str] | None = None,
    context_resume: str = "",
    attachments: list[dict] | None = None,
    application_kind: str = "job",
    target_label: str = "Position",
    company_match_report: str = "",
    possible_use_cases: list[str] | None = None,
    top_candidate_insights: str = "",
) -> str:
    cover_letter = normalize_export_text(
        cover_letter
    )
    profile_summary = normalize_export_text(
        profile_summary
    )
    context_resume = normalize_export_text(
        context_resume
    )
    matched_tags = matched_tags or []
    missing_tags = missing_tags or []
    job_required_tags = job_required_tags or []
    attachments = attachments or []
    possible_use_cases = possible_use_cases or []
    target_label = normalize_export_text(
        target_label
    )
    include_context_resume = bool(
        context_resume.strip()
    ) and not _has_resume_attachment(
        attachments
    )

    job_title = normalize_export_text(
        unescape(
            job_title or ""
        )
    )

    company = normalize_export_text(
        unescape(_company_display(company))
    )

    today = date.today().strftime(
        "%d.%m.%Y"
    )

    skills_html = "\n".join(
        f"<li>{escape(export_label_tag(tag))}</li>"
        for tag in profile_tags
    )

    missing_skills_html = "\n".join(
        f"<li>{escape(export_label_tag(tag))}</li>"
        for tag in missing_tags
    )
    use_cases_html = "\n".join(
        f"<li>{escape(normalize_export_text(item))}</li>"
        for item in possible_use_cases
        if str(item).strip()
    )

    match_total = len(job_required_tags)
    match_count = len(matched_tags)

    if match_total:
        match_percentage = round(
            match_count / match_total * 100
        )
        match_summary = (
            f"Skill-Match: {match_count}/{match_total} "
            f"Anforderungen erfüllt ({match_percentage}%)"
        )
    else:
        match_summary = (
            "Skill-Match: Noch keine Anforderungen erkannt"
        )

    cover_letter_html = escape(
        cover_letter
    ).replace(
        "\n",
        "<br>",
    )

    profile_summary_html = escape(
        profile_summary
    ).replace(
        "\n",
        "<br>",
    )

    context_resume_html = escape(
        context_resume
    ).replace(
        "\n",
        "<br>",
    )
    company_match_report_html = escape(
        normalize_export_text(company_match_report)
    ).replace(
        "\n",
        "<br>",
    )
    top_candidate_insights_html = _insight_cards_html(
        top_candidate_insights
    )

    if application_kind == "initiative":
        subtitle = "Initiativbewerbungsmappe aus Company Match"
        target_info_title = "Company-Match-Informationen"
        analysis_title = "Company-Match-Kontext"
        match_summary = (
            "Initiativbewerbung ohne konkrete Stellenanzeige. "
            "Die Auswertung basiert auf Company Match, Profilskills "
            "und hochgeladenem Kontext."
        )
    else:
        subtitle = "Automatisch erzeugte Bewerbungsmappe"
        target_info_title = "Stelleninformationen"
        analysis_title = "Anforderungsanalyse"

    match_summary = normalize_export_text(
        match_summary
    )

    attachment_items = []

    for index, item in enumerate(
        attachments,
        start=1,
    ):
        name = item.get("name", "Anhang")
        archive_name = item.get("archive_name")
        preview_uri = _attachment_preview_data_uri(item)
        display_title = attachment_display_title(
            item,
            index,
        )
        original_note = _attachment_original_note(
            str(name),
            display_title,
        )

        if not _is_curated_attachment_title(
            display_title
        ):
            continue

        if archive_name:
            href = quote(
                f"anlagen/{archive_name}",
                safe="/._-",
            )
            title_html = (
                f'<a href="{escape(href)}">'
                f"{escape(display_title)}</a>"
            )
        else:
            title_html = f"<strong>{escape(display_title)}</strong>"

        attachment_items.append(
            '<li class="attachment-item">'
            f"{title_html}"
            f"<br>{escape(_attachment_overview_reason(item.get('reason', 'Relevanter Nachweis')))}"
            f"{'<br>' + original_note if original_note else ''}"
            "</li>"
        )

    curated_attachment_overview_exists = any(
        _is_attachment_overview_item(item)
        or _is_attachment_overview_title(
            attachment_display_title(
                item,
                index,
            )
        )
        for index, item in enumerate(attachments, start=1)
    )

    attachments_html = "\n".join(
        attachment_items
    )

    attachment_count_text = f"{len(attachment_items)} Anlage(n) aufgeführt."
    attachments_section = ""

    if attachments_html and not curated_attachment_overview_exists:
        attachments_section = f"""
<section class="page attachments-page">

    <div class="header">

        <span class="logo">
            <img src="{logo_data_uri()}" alt="{APP_NAME} Logo">
            {APP_NAME}
        </span>

    </div>

    <h1>Anlagenübersicht</h1>

    <p>
        {escape(attachment_count_text)}
        Die folgenden Nachweise wurden für diese Mappe kuratiert.
        Ausgewählte Originalanlagen werden der finalen PDF danach
        vollständig beigefügt.
    </p>

    <ol class="attachments">
        {attachments_html}
    </ol>

</section>
"""

    context_resume_section = ""

    if include_context_resume:
        context_resume_section = f"""
<section class="page resume-page">

    <div class="header">

        <span class="logo">
            <img src="{logo_data_uri()}" alt="{APP_NAME} Logo">
            {APP_NAME}
        </span>

    </div>

    <h1>Kontextbezogener Lebenslauf</h1>

    <div class="resume">
        {context_resume_html}
    </div>

</section>
"""

    target_info_box = f"""
    <div class="job-box compact-box">
        <p>
            <strong>{escape(target_label)}:</strong><br>
            {escape(job_title)}
        </p>

        <p>
            <strong>Unternehmen:</strong><br>
            {escape(company)}
        </p>
    </div>
"""

    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">

<title>
{APP_NAME} Bewerbungsmappe
</title>

<style>

@page {{
    size: A4;
    margin: 18mm 16mm;
}}

html {{
    font-size: 11pt;
}}

body {{
    font-family: Arial, Helvetica, sans-serif;
    margin: 0;
    background: #f3f4f6;
    color: #111827;
    line-height: 1.48;
    overflow-wrap: break-word;
}}

.page {{
    width: 210mm;
    min-height: 297mm;
    margin: 20mm auto;
    padding: 20mm 22mm;
    background: white;
    box-sizing: border-box;
    page-break-after: always;
    break-after: page;
    overflow: visible;
}}

.compact-page {{
    page-break-after: always;
    break-after: page;
}}

.header {{
    border-bottom: 2px solid #2563eb;
    padding-bottom: 10px;
    margin-bottom: 24px;
    page-break-inside: avoid;
    break-inside: avoid;
}}

.logo {{
    display: inline-flex;
    align-items: center;
    gap: 10px;
    font-size: 28px;
    font-weight: bold;
    color: #0f172a;
}}

.logo img {{
    width: 34px;
    height: 34px;
    vertical-align: middle;
}}

.subtitle {{
    color: #6b7280;
}}

.date {{
    float: right;
    color: #6b7280;
}}

h1 {{
    margin-top: 0;
    margin-bottom: 16px;
    page-break-after: avoid;
    break-after: avoid;
    font-size: 28px;
    line-height: 1.15;
}}

h2 {{
    color: #2563eb;
    margin-top: 20px;
    margin-bottom: 10px;
    page-break-after: avoid;
    break-after: avoid;
    font-size: 18px;
    line-height: 1.2;
}}

h1,
h2,
h3 {{
    page-break-inside: avoid;
    break-inside: avoid;
}}

.job-box,
.insight-card {{
    page-break-inside: avoid;
    break-inside: avoid;
}}

.section-block {{
    margin: 0 0 18px;
    page-break-inside: avoid;
    break-inside: avoid;
}}

.flow-block {{
    margin: 0 0 18px;
}}

.letter-text {{
    font-size: 11.2pt;
    line-height: 1.58;
    margin: 0;
}}

.profile-text {{
    line-height: 1.45;
    margin-bottom: 18px;
}}

.skills {{
    columns: 2;
    column-gap: 18mm;
    margin: 0 0 18px;
    padding-left: 18px;
}}

.skills li {{
    margin-bottom: 8px;
    page-break-inside: avoid;
    break-inside: avoid;
}}

.resume {{
    font-size: 10.8pt;
    line-height: 1.44;
    white-space: normal;
}}

.resume-page {{
    padding-top: 20mm;
    padding-bottom: 18mm;
}}

.resume-page h1 {{
    margin-bottom: 12px;
}}

.resume strong {{
    color: #0f172a;
}}

.attachments {{
    margin: 18px 0 0;
    padding-left: 22px;
}}

.attachment-item {{
    margin-bottom: 14px;
    padding-left: 4px;
    line-height: 1.42;
    page-break-inside: avoid;
    break-inside: avoid;
}}

.attachment-original {{
    color: #6b7280;
    font-size: 11px;
}}

.embedded-preview {{
    width: 100%;
    max-height: 235mm;
    object-fit: contain;
    border: 1px solid #e5e7eb;
}}

.attachment-page {{
    padding-bottom: 15mm;
}}

.attachments-page {{
    page-break-before: always;
    break-before: page;
    page-break-after: auto;
    break-after: auto;
}}

.insights-section {{
    margin-top: 6px;
}}

.job-box {{
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    padding: 20px;
    border-radius: 8px;
}}

.compact-box {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 22px;
}}

.compact-box p {{
    margin: 0;
}}

.insight-grid {{
    display: grid;
    gap: 14px;
}}

.insight-card {{
    border: 1px solid #dbeafe;
    border-left: 4px solid #2563eb;
    background: #f8fafc;
    padding: 14px 16px;
    border-radius: 8px;
}}

.insight-card h3 {{
    margin: 0 0 6px 0;
    color: #0f172a;
    font-size: 16px;
}}

.insight-card p {{
    margin: 0;
    color: #374151;
    line-height: 1.45;
}}

.footer {{
    max-width: 210mm;
    margin: 0 auto 16mm;
    padding: 0 22mm;
    box-sizing: border-box;
    color: #6b7280;
    font-size: 12px;
}}

@media print {{

    body {{
        background: white;
        color: #111827;
    }}

    .page {{
        width: auto;
        min-height: auto;
        margin: 0;
        padding: 0;
        box-shadow: none;
        page-break-after: always;
        break-after: page;
    }}

    .page:last-of-type {{
        page-break-after: auto;
        break-after: auto;
    }}

    .footer {{
        margin: 0;
        padding: 0;
    }}

    .skills {{
        columns: 2;
    }}

    a {{
        color: inherit;
        text-decoration: none;
    }}
}}

</style>
</head>

<body>

<section class="page">

    <div class="header">

        <span class="logo">
            <img src="{logo_data_uri()}" alt="{APP_NAME} Logo">
            {APP_NAME}
        </span>

        <span class="date">
            {today}
        </span>

        <div class="subtitle">
            {escape(subtitle)}
        </div>

    </div>

    <h1>Anschreiben</h1>

    <h2>
        {escape(job_title)}
    </h2>

    <p class="letter-text">
        {cover_letter_html}
    </p>

</section>

<section class="page">

    <div class="header">

        <span class="logo">
            <img src="{logo_data_uri()}" alt="{APP_NAME} Logo">
            {APP_NAME}
        </span>

    </div>

    <h1>Profil und Kompetenzprofil</h1>

    <div class="section-block">
        {target_info_box}
    </div>

    <div class="flow-block">
    <h2>Profil</h2>

    <p class="profile-text">
        {profile_summary_html}
    </p>
    </div>

    <div class="section-block">
    <h2>Kompetenzen</h2>

    <ul class="skills">
        {skills_html}
    </ul>
    </div>

    <div class="section-block">
    <h2>{escape(analysis_title)}</h2>

    <p>
        {escape(match_summary)}
    </p>
    </div>

    {f'''
    <h2>Mögliche Einsatzfelder</h2>

    <ul class="skills">
        {use_cases_html}
    </ul>
    ''' if use_cases_html else ""}

    {f'''
    <div class="insights-section">

    <h2>Top Candidate Insights</h2>

    <div class="insight-grid">
        {top_candidate_insights_html}
    </div>

    </div>
    ''' if top_candidate_insights_html else ""}

    {f'''
    <h2>Company Match Report</h2>

    <p>
        {company_match_report_html}
    </p>
    ''' if company_match_report_html else ""}

    <div class="section-block">
    <h2>Fehlende Anforderungen</h2>

    <ul class="skills">
        {missing_skills_html or "<li>Keine fehlenden Anforderungen erkannt.</li>"}
    </ul>
    </div>

</section>

{context_resume_section}

{attachments_section}

<div class="footer">
    Erstellt mit {APP_NAME} - Lokale KI-Auswertung mittels Ollama + Qwen
</div>

</body>
</html>
"""

