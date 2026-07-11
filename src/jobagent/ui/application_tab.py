import re
import zipfile
from io import BytesIO
from xml.etree import ElementTree

import streamlit as st
from pypdf import PdfReader, PdfWriter

from jobagent.models.tag_labels import label_tag
from jobagent.services.application_html_service import (
    attachment_display_title,
    generate_application_html,
)
from jobagent.services.application_service import (
    generate_company_initiative_letter,
    generate_context_resume,
    generate_cover_letter,
    last_cover_letter_debug,
)
from jobagent.services.application_package_service import (
    application_zip_bytes,
)
from jobagent.services.application_pdf_service import (
    html_pdf_renderer_status,
    is_html_pdf_renderer_available,
    render_final_application_pdf,
)
from jobagent.services.candidate_insight_service import (
    extract_candidate_insights,
    format_candidate_insights,
)
from jobagent.services.candidate_insight_ranker import (
    build_candidate_insight_views,
    format_candidate_insight_views,
    format_ranked_candidate_insights,
    rank_candidate_insights,
)
from jobagent.services.company_match_report_service import (
    company_match_report_key,
)
from jobagent.services.document_parser import extract_text_from_pdf
from jobagent.services.export_text_service import normalize_export_text
from jobagent.services.job_skill_service import (
    compare_profile_to_job,
    extract_job_required_skills,
)
from jobagent.services.profile_summary_service import (
    generate_profile_summary,
)

EVIDENCE_TERMS = [
    "lebenslauf",
    "curriculum vitae",
    "resume",
    "cv",
    "zeugnis",
    "arbeitszeugnis",
    "zertifikat",
    "zertifizierung",
    "certificate",
    "certification",
    "bescheinigung",
    "teilnahmebescheinigung",
    "abschluss",
    "diplom",
    "urkunde",
    "pruefung",
    "prüfung",
    "exam",
    "aws",
    "azure",
    "microsoft",
    "itil",
    "scrum",
    "pmp",
]

RESUME_TERMS = [
    "lebenslauf",
    "curriculum vitae",
    "resume",
    "cv",
]

RESUME_SECTION_TERMS = [
    "persoenliche daten",
    "persönliche daten",
    "berufserfahrung",
    "berufliche erfahrung",
    "beruflicher werdegang",
    "werdegang",
    "ausbildung",
    "studium",
    "kenntnisse",
    "faehigkeiten",
    "fähigkeiten",
    "kompetenzen",
    "qualifikationen",
    "sprachkenntnisse",
    "edv-kenntnisse",
    "it-kenntnisse",
    "projekterfahrung",
    "profil",
]

ATTACHMENT_DETECTION_VERSION = 2


def _job_key(job) -> str:
    return "|".join(
        [
            job.title or "",
            job.company or "",
            job.url or "",
            getattr(job, "source_name", None) or "",
        ]
    )


def _company_display(job) -> str:
    if job.company:
        return job.company

    return "Arbeitgeber nicht eindeutig genannt"


def _source_display(job) -> str | None:
    source_name = getattr(job, "source_name", None)

    if not source_name:
        return None

    return source_name


def _clean_description(job) -> str:
    return re.sub(
        "<.*?>",
        "",
        job.description or "",
    )


def _extract_text_from_txt(uploaded_file) -> str:
    data = uploaded_file.getvalue()

    for encoding in ["utf-8-sig", "utf-8", "cp1252"]:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue

    return data.decode(
        "utf-8",
        errors="ignore",
    )


def _extract_text_from_docx(uploaded_file) -> str:
    data = uploaded_file.getvalue()

    with zipfile.ZipFile(BytesIO(data)) as archive:
        xml = archive.read("word/document.xml")

    root = ElementTree.fromstring(xml)
    namespace = {
        "w": (
            "http://schemas.openxmlformats.org/"
            "wordprocessingml/2006/main"
        )
    }

    paragraphs = []

    for paragraph in root.findall(".//w:p", namespace):
        texts = [
            node.text
            for node in paragraph.findall(".//w:t", namespace)
            if node.text
        ]

        if texts:
            paragraphs.append("".join(texts))

    return "\n".join(paragraphs)


def _context_file_signature(uploaded_file) -> tuple[str, int, int]:
    return (
        uploaded_file.name,
        uploaded_file.size,
        ATTACHMENT_DETECTION_VERSION,
    )


def _extract_context_file(uploaded_file) -> str:
    name = uploaded_file.name.lower()

    if name.endswith(".pdf"):
        return extract_text_from_pdf(
            BytesIO(uploaded_file.getvalue())
        )

    if name.endswith(".txt"):
        return _extract_text_from_txt(uploaded_file)

    if name.endswith(".docx"):
        return _extract_text_from_docx(uploaded_file)

    raise ValueError(
        f"Dateityp wird nicht unterstützt: {uploaded_file.name}"
    )


def _application_context_text(uploaded_files) -> str:
    cache = st.session_state.setdefault(
        "application_context_cache",
        {},
    )
    parts = []

    for uploaded_file in uploaded_files or []:
        signature = _context_file_signature(
            uploaded_file
        )

        if signature not in cache:
            cache[signature] = _extract_context_file(
                uploaded_file
            )

        text = cache[signature]

        if text.strip():
            parts.append(
                f"Quelle: {uploaded_file.name}\n{text.strip()}"
            )

    return "\n\n---\n\n".join(parts)


def _safe_archive_name(name: str) -> str:
    clean_name = re.sub(
        r"[^A-Za-z0-9._ -]+",
        "_",
        name or "anhang",
    ).strip()

    return clean_name or "anhang"


def _evidence_reason(
    name: str,
    text: str,
) -> str | None:
    name = name.lower()
    text_lower = (text or "").lower()

    if any(term in name for term in EVIDENCE_TERMS):
        return "Dateiname weist auf Zeugnis, Zertifikat oder Nachweis hin."

    if any(term in text_lower for term in EVIDENCE_TERMS):
        return "Inhalt weist auf Zeugnis, Zertifikat oder Nachweis hin."

    return None


def _is_resume_attachment(
    name: str,
    text: str,
) -> bool:
    name_lower = (name or "").lower()
    text_lower = (text or "").lower()

    if any(
        term in name_lower or term in text_lower
        for term in RESUME_TERMS
    ):
        return True

    section_score = _resume_section_score(
        text_lower
    )

    if section_score >= 3:
        return True

    contact_signal = bool(
        re.search(
            r"[\w.+-]+@[\w.-]+\.[a-z]{2,}",
            text_lower,
        )
    ) or bool(
        re.search(
            r"(\+49|0)\s?\d[\d\s()/.-]{6,}",
            text_lower,
        )
    )

    return contact_signal and section_score >= 2


def _resume_section_score(text: str) -> int:
    found_terms = set()

    for raw_line in text.splitlines():
        line = re.sub(
            r"\s+",
            " ",
            raw_line.strip().lower(),
        )

        if not line or len(line) > 70:
            continue

        normalized_line = re.sub(
            r"[:|•\-–—]+$",
            "",
            line,
        ).strip()

        for term in RESUME_SECTION_TERMS:
            if (
                normalized_line == term
                or normalized_line.startswith(f"{term} ")
            ):
                found_terms.add(term)

    return len(found_terms)


def _attachment_reason(uploaded_file, text: str) -> str | None:
    return _evidence_reason(
        uploaded_file.name,
        text,
    )


def _pdf_page_bytes(
    reader: PdfReader,
    page_index: int,
) -> bytes:
    writer = PdfWriter()
    writer.add_page(
        reader.pages[page_index]
    )
    buffer = BytesIO()
    writer.write(buffer)

    return buffer.getvalue()


def _pdf_page_text(page_bytes: bytes) -> str:
    return extract_text_from_pdf(
        BytesIO(page_bytes)
    )


def _pdf_page_attachment_name(
    uploaded_file,
    page_number: int,
) -> str:
    base_name = re.sub(
        r"\.pdf$",
        "",
        uploaded_file.name,
        flags=re.IGNORECASE,
    )

    return f"{base_name}-anlage-seite-{page_number}.pdf"


def _pdf_attachments(uploaded_file) -> list[dict]:
    file_bytes = uploaded_file.getvalue()
    reader = PdfReader(
        BytesIO(file_bytes)
    )
    attachments = []

    for page_index in range(len(reader.pages)):
        page_number = page_index + 1
        page_bytes = _pdf_page_bytes(
            reader,
            page_index,
        )
        page_name = _pdf_page_attachment_name(
            uploaded_file,
            page_number,
        )
        page_text = _pdf_page_text(
            page_bytes
        )
        reason = _evidence_reason(
            page_name,
            page_text,
        )
        is_resume = _is_resume_attachment(
            page_name,
            page_text,
        )

        if not reason and not is_resume:
            continue

        attachments.append(
            {
                "name": page_name,
                "archive_name": _safe_archive_name(
                    page_name
                ),
                "reason": (
                    f"{reason or 'Lebenslauf erkannt.'} Extrahiert aus "
                    f"{uploaded_file.name}, Seite {page_number}."
                ),
                "bytes": page_bytes,
                "kind": (
                    "resume"
                    if is_resume
                    else "evidence"
                ),
            }
        )

    return attachments


def _file_attachment(uploaded_file) -> dict | None:
    signature = _context_file_signature(
        uploaded_file
    )
    text = st.session_state.get(
        "application_context_cache",
        {},
    ).get(signature, "")
    reason = _attachment_reason(
        uploaded_file,
        text,
    )
    is_resume = _is_resume_attachment(
        uploaded_file.name,
        text,
    )

    if not reason and not is_resume:
        return None

    return {
        "name": uploaded_file.name,
        "archive_name": _safe_archive_name(
            uploaded_file.name
        ),
        "reason": reason or "Lebenslauf erkannt.",
        "bytes": uploaded_file.getvalue(),
        "kind": (
            "resume"
            if is_resume
            else "evidence"
        ),
    }


def _attachments_for_file(uploaded_file) -> list[dict]:
    name = uploaded_file.name.lower()

    if name.endswith(".pdf"):
        page_attachments = _pdf_attachments(
            uploaded_file
        )

        if page_attachments:
            return page_attachments

    file_attachment = _file_attachment(
        uploaded_file
    )

    if file_attachment:
        return [file_attachment]

    return []


def _application_attachments(uploaded_files) -> list[dict]:
    cache = st.session_state.setdefault(
        "application_attachment_cache",
        {},
    )
    attachments = []

    for uploaded_file in uploaded_files or []:
        signature = _context_file_signature(
            uploaded_file
        )

        if signature not in cache:
            cache[signature] = _attachments_for_file(
                uploaded_file
            )

        attachments.extend(
            cache[signature]
        )

    return attachments


def _uploaded_files_as_manual_attachments(
    uploaded_files,
    reason: str = "Manuell für die Initiativmappe ausgewählte Anlage.",
) -> list[dict]:
    attachments = []

    for uploaded_file in uploaded_files or []:
        attachments.append(
            {
                "name": uploaded_file.name,
                "archive_name": _safe_archive_name(
                    uploaded_file.name
                ),
                "reason": reason,
                "bytes": uploaded_file.getvalue(),
                "kind": "manual",
            }
        )

    return attachments


def _merge_attachments(
    *attachment_groups: list[dict],
) -> list[dict]:
    merged = []
    seen = set()

    for group in attachment_groups:
        for attachment in group or []:
            key = (
                attachment.get("archive_name")
                or attachment.get("name")
                or ""
            ).lower()
            size = len(
                attachment.get("bytes")
                or b""
            )
            signature = (
                key,
                size,
            )

            if signature in seen:
                continue

            seen.add(
                signature
            )
            merged.append(
                attachment
            )

    return merged


def _application_zip_bytes(
    html_content: str,
    attachments: list[dict],
    html_name: str = "bewerbungsmappe.html",
    extra_files: list[dict] | None = None,
) -> bytes:
    return application_zip_bytes(
        html_content,
        attachments,
        html_name,
        extra_files=extra_files,
    )


def _application_pdf_bytes(
    html_content: str,
    attachments: list[dict] | None = None,
) -> bytes | None:
    return render_final_application_pdf(
        html_content,
        attachments or [],
    )


def _pdf_renderer_status_text() -> str:
    status = html_pdf_renderer_status()

    return (
        "PDF-Rendererstatus: "
        f"renderer_available={status.get('renderer_available')}, "
        f"renderer_name={status.get('renderer_name') or '-'}, "
        f"renderer_path={status.get('renderer_path') or '-'}, "
        f"pdfkit_import_ok={status.get('pdfkit_import_ok')}"
    )


def _download_file_stem(
    prefix: str,
    company_name: str,
) -> str:
    profile = st.session_state.get(
        "active_profile"
    ) or st.session_state.get(
        "profile"
    )
    profile_name = getattr(
        profile,
        "name",
        "",
    )

    if isinstance(profile, dict):
        profile_name = profile.get(
            "name",
            "",
        )

    parts = [
        prefix,
        company_name,
        profile_name or "CareerHub",
    ]
    clean_parts = [
        _safe_archive_name(part).replace(
            " ",
            "_",
        )
        for part in parts
        if str(part).strip()
    ]

    return "_".join(
        clean_parts
    )


def _has_resume_attachment(attachments: list[dict]) -> bool:
    return any(
        attachment.get("kind") == "resume"
        for attachment in attachments
    )


def _profile_summary(profile_tags: set[str]) -> str:
    tags_key = tuple(sorted(profile_tags))
    cache_key = "application_profile_summary"
    cache_tags_key = "application_profile_summary_tags"

    if st.session_state.get(cache_tags_key) != tags_key:
        st.session_state[cache_key] = generate_profile_summary(
            list(tags_key)
        )
        st.session_state[cache_tags_key] = tags_key

    return st.session_state.get(cache_key, "")


def _job_skill_analysis(job, clean_description: str):
    job_key = _job_key(job)
    cache_key = "application_job_skill_analysis"

    cached = st.session_state.get(cache_key)

    if cached and cached.get("job_key") == job_key:
        return cached["job_tags"]

    job_tags = extract_job_required_skills(
        clean_description
    )

    st.session_state[cache_key] = {
        "job_key": job_key,
        "job_tags": job_tags,
    }

    return job_tags


def _cover_letter_key(
    job,
    profile_tags: set[str],
    profile_context: str,
) -> str:
    return "|".join(
        [
            _job_key(job),
            ",".join(sorted(profile_tags)),
            str(hash(profile_context)),
        ]
    )


def _resume_key(
    job,
    profile_tags: set[str],
    profile_context: str,
) -> str:
    return "|".join(
        [
            _job_key(job),
            ",".join(sorted(profile_tags)),
            str(hash(profile_context)),
        ]
    )


def _company_match_key(
    company_match,
    profile_tags: set[str],
    profile_context: str = "",
) -> str:
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

    return "|".join(
        [
            company_name,
            ",".join(sorted(profile_tags)),
            str(getattr(company_match, "total_score", 0)),
            str(hash(profile_context)),
        ]
    )


def _company_match_context(company_match) -> str:
    company = getattr(
        company_match,
        "company",
        None,
    )

    if not company:
        return ""

    lines = [
        f"Unternehmen: {company.name}",
        (
            "Application Recommendation: "
            f"{getattr(company_match, 'application_recommendation', '')}"
        ),
        f"Company Match Score: {getattr(company_match, 'total_score', 0)}",
        "Gruende: "
        + "; ".join(getattr(company_match, "reasons", []) or []),
        "Risiken: "
        + "; ".join(getattr(company_match, "risk_flags", []) or []),
        "Erkannte Skills: "
        + ", ".join(getattr(company, "detected_skills", []) or []),
        "Erkannte Kompetenzen: "
        + ", ".join(getattr(company, "detected_competencies", []) or []),
        "Moegliche Einsatzfelder: "
        + ", ".join(getattr(company, "possible_use_cases", []) or []),
        "Schwerpunkte: "
        + ", ".join(getattr(company, "focus_areas", []) or []),
        "Qualifikationsanforderungen: "
        + ", ".join(
            getattr(company, "qualification_requirements", []) or []
        ),
        "Arbeitsmodelle: "
        + ", ".join(getattr(company, "work_models", []) or []),
        "Standorte: "
        + ", ".join(getattr(company, "locations", []) or []),
    ]
    matching_jobs = getattr(
        company_match,
        "matching_jobs",
        [],
    )

    if matching_jobs:
        lines.append(
            "Passende Jobs als Signale: "
            + "; ".join(
                job.title
                for job in matching_jobs[:5]
                if getattr(job, "title", None)
            )
        )

    return "\n".join(
        line
        for line in lines
        if line.strip()
    )


def _company_match_report_context(company_match) -> str:
    if not company_match:
        return ""

    report_key = company_match_report_key(
        company_match
    )
    reports = st.session_state.get(
        "company_match_reports",
        {},
    )
    report = reports.get(
        report_key,
    )

    if report:
        return report

    if st.session_state.get(
        "selected_company_match_report_key"
    ) == report_key:
        return st.session_state.get(
            "selected_company_match_report",
            "",
        )

    return ""


def _company_initiative_context(company_match) -> str:
    parts = [
        _company_match_context(
            company_match
        )
    ]
    report = _company_match_report_context(
        company_match
    )

    if report:
        parts.append(
            "Company Match Report:\n" + report
        )

    return "\n\n".join(
        part
        for part in parts
        if part.strip()
    )


def _candidate_insight_prompt_context(
    raw_context: str,
    company_match=None,
) -> str:
    raw_context = raw_context or ""

    if not raw_context.strip():
        return ""

    insights = extract_candidate_insights(
        raw_context
    )
    report = _company_match_report_context(
        company_match
    )
    ranked_insights = rank_candidate_insights(
        insights,
        company_match=company_match,
        company_match_report=report,
    )
    ranked_insight_text = format_ranked_candidate_insights(
        ranked_insights
    )
    insight_text = format_candidate_insights(
        insights
    )

    return "\n\n".join(
        [
            ranked_insight_text,
            insight_text,
            "Rohtextauszug aus Kontextdokumenten:\n" + raw_context,
        ]
    )


def _top_candidate_insights_from_context(candidate_context: str) -> str:
    candidate_context = candidate_context or ""

    if not candidate_context.strip():
        return ""

    marker = "\n\nCandidate Insights:"
    index = candidate_context.find(
        marker
    )

    if index >= 0:
        return candidate_context[:index].strip()

    raw_marker = "\n\nRohtextauszug"
    index = candidate_context.find(
        raw_marker
    )

    if index >= 0:
        return candidate_context[:index].strip()

    return candidate_context.strip()


def _candidate_insight_view_context(
    raw_context: str,
    company_match=None,
) -> str:
    raw_context = raw_context or ""

    if not raw_context.strip():
        return ""

    insights = extract_candidate_insights(
        raw_context
    )
    report = _company_match_report_context(
        company_match
    )
    ranked_insights = rank_candidate_insights(
        insights,
        company_match=company_match,
        company_match_report=report,
    )
    views = build_candidate_insight_views(
        ranked_insights
    )

    return format_candidate_insight_views(
        views
    )


def _company_application_html(
    selected_company_match,
    initiative_letter: str,
    profile_tags: set[str],
    candidate_insight_context: str = "",
    attachments: list[dict] | None = None,
) -> str:
    company = getattr(
        selected_company_match,
        "company",
        None,
    )
    company_name = getattr(
        company,
        "name",
        "Zielunternehmen",
    )
    possible_use_cases = getattr(
        company,
        "possible_use_cases",
        [],
    ) or []
    report = _company_match_report_context(
        selected_company_match
    )
    top_candidate_insights = _candidate_insight_view_context(
        candidate_insight_context,
        selected_company_match,
    ) or _top_candidate_insights_from_context(
        candidate_insight_context
    )

    return generate_application_html(
        cover_letter=initiative_letter,
        profile_summary=_profile_summary(
            profile_tags
        ),
        profile_tags=sorted(profile_tags),
        job_title="Initiativbewerbung",
        company=company_name,
        context_resume="",
        attachments=attachments or [],
        application_kind="initiative",
        target_label="Bewerbungsziel",
        company_match_report=report,
        possible_use_cases=possible_use_cases,
        top_candidate_insights=top_candidate_insights,
    )


def _render_company_application_export(
    selected_company_match,
    initiative_letter: str,
    profile_tags: set[str],
    candidate_insight_context: str,
    attachments: list[dict],
) -> None:
    if not selected_company_match or not initiative_letter:
        st.info(
            "Fuer den Export wird ein vorgemerktes Company Match "
            "und eine erzeugte Initiativbewerbung benoetigt."
        )
        return

    company = getattr(
        selected_company_match,
        "company",
        None,
    )
    company_name = getattr(
        company,
        "name",
        "Zielunternehmen",
    )
    file_stem = _download_file_stem(
        "Initiative",
        company_name,
    )
    html_name = f"{file_stem}.html"
    st.markdown("### Initiativbewerbungsmappe exportieren")
    st.markdown("#### Anlagen für den Export")

    detected_attachments = attachments or []

    if detected_attachments:
        st.write("Automatisch erkannte Anlagen:")
        selected_indexes = []

        for index, attachment in enumerate(
            detected_attachments
        ):
            display_title = attachment_display_title(
                attachment,
                index + 1,
            )
            selected = st.checkbox(
                (
                    f"{display_title} - "
                    f"{normalize_export_text(attachment.get('reason', 'Relevante Anlage'))}"
                ),
                value=True,
                key=f"company_initiative_attachment_{file_stem}_{index}",
            )

            if selected:
                selected_indexes.append(
                    index
                )

        selected_attachments = [
            detected_attachments[index]
            for index in selected_indexes
        ]
    else:
        st.caption(
            "Noch keine automatisch erkannten Anlagen vorhanden."
        )
        selected_attachments = []

    extra_attachment_files = st.file_uploader(
        "Weitere Anlagen für die Initiativmappe hochladen",
        type=[
            "pdf",
            "txt",
            "docx",
        ],
        accept_multiple_files=True,
        key=f"company_initiative_export_attachments_{file_stem}",
    )
    manual_attachments = _uploaded_files_as_manual_attachments(
        extra_attachment_files,
        reason=(
            "Manuell für die Initiativmappe ausgewählte "
            "Projektunterlage oder Anlage."
        ),
    )
    export_attachments = _merge_attachments(
        selected_attachments,
        manual_attachments,
    )

    if export_attachments:
        st.write("Anlagenübersicht für den Export:")

        for index, attachment in enumerate(
            export_attachments,
            start=1,
        ):
            display_title = attachment_display_title(
                attachment,
                index,
            )
            st.write(
                f"- {display_title} - "
                f"{normalize_export_text(attachment.get('reason', 'Relevante Anlage'))}"
            )

    html_content = _company_application_html(
        selected_company_match=selected_company_match,
        initiative_letter=initiative_letter,
        profile_tags=profile_tags,
        candidate_insight_context=candidate_insight_context,
        attachments=export_attachments,
    )

    full_pdf_content = None
    html_pdf_renderer_available = is_html_pdf_renderer_available()

    if html_pdf_renderer_available:
        full_pdf_content = _application_pdf_bytes(
            html_content,
            export_attachments,
        )

    if full_pdf_content:
        st.download_button(
            label="Finale Bewerbungsmappe als PDF herunterladen",
            data=full_pdf_content,
            file_name=f"{file_stem}.pdf",
            mime="application/pdf",
        )
    else:
        st.info(
            "Fuer automatische PDF-Erzeugung bitte WeasyPrint oder "
            "wkhtmltopdf installieren. Alternativ die HTML-Datei aus "
            "dem ZIP im Browser oeffnen und als PDF drucken."
        )
        st.caption(
            _pdf_renderer_status_text()
        )

    zip_content = _application_zip_bytes(
        html_content,
        export_attachments,
        html_name=html_name,
    )

    st.download_button(
        label="Exportpaket als ZIP herunterladen",
        data=zip_content,
        file_name=f"{file_stem}.zip",
        mime="application/zip",
    )

def _render_company_initiative_section(
    selected_company_match,
    profile_tags: set[str],
) -> None:
    if not selected_company_match:
        st.info(
            "Kein Company Match vorgemerkt. Im Tab 'Company Match' kann "
            "eine Firma als Initiativziel vorgemerkt werden."
        )
        return

    company = getattr(
        selected_company_match,
        "company",
        None,
    )
    company_name = getattr(
        company,
        "name",
        "das vorgemerkte Unternehmen",
    )

    st.markdown("### Initiativbewerbung aus Company Match")
    st.info(
        f"Vorgemerktes Company Match: {company_name}. "
        "Die Initiativbewerbung nutzt Company-Match-Signale "
        "und aktive Profilskills, aber keine konkrete Stellenanzeige."
    )
    st.write(
        f"**Company Match Score:** "
        f"{getattr(selected_company_match, 'total_score', 0)}"
    )

    possible_use_cases = getattr(
        company,
        "possible_use_cases",
        [],
    ) or []
    strategic_reasons = [
        reason
        for reason in getattr(selected_company_match, "reasons", []) or []
        if "Strategic Fit:" in reason
    ]
    report = _company_match_report_context(
        selected_company_match
    )

    if possible_use_cases:
        st.write("**Moegliche Einsatzfelder:**")

        for use_case in possible_use_cases:
            st.write(
                f"- {use_case}"
            )

    if strategic_reasons:
        st.write("**Strategische Fit-Gruende:**")

        for reason in strategic_reasons:
            st.write(
                f"- {reason}"
            )

    if report:
        with st.expander(
            "Company Match Report anzeigen",
            expanded=False,
        ):
            st.markdown(
                report
            )

    with st.expander(
        "Company-Match-Kontext anzeigen",
        expanded=False,
    ):
        st.text_area(
            "Company-Match-Kontext",
            _company_initiative_context(selected_company_match),
            height=220,
        )

    st.markdown("#### Kontextdokumente")
    context_files = st.file_uploader(
        "CV, Projektübersicht, Zeugnisse, Zertifikate oder Bewerbungsmappe für die Initiativbewerbung hochladen",
        type=[
            "pdf",
            "txt",
            "docx",
        ],
        accept_multiple_files=True,
        key="company_initiative_context_uploads",
    )
    profile_context = ""
    candidate_insight_context = ""
    attachments = []

    if context_files:
        try:
            profile_context = _application_context_text(
                context_files
            )
            attachments = _application_attachments(
                context_files
            )
            candidate_insight_context = _candidate_insight_prompt_context(
                profile_context,
                selected_company_match,
            )
            st.success(
                f"{len(context_files)} Kontextdatei(en) geladen, "
                f"{len(profile_context)} Zeichen extrahiert."
            )

            with st.expander(
                "Priorisierte Candidate Insights anzeigen",
                expanded=False,
            ):
                st.text_area(
                    "Priorisierte und strukturierte Candidate Insights",
                    candidate_insight_context[:6000],
                    height=260,
                )

            with st.expander(
                "Extrahierten Kontext anzeigen",
                expanded=False,
            ):
                st.text_area(
                    "Extrahierter Kontext für die Initiativbewerbung",
                    profile_context[:6000],
                        height=260,
                )

            if attachments:
                with st.expander(
                    "Erkannte Anlagen für die Initiativmappe",
                    expanded=False,
                ):
                    for attachment in attachments:
                        st.write(
                            f"- {attachment['name']} - "
                            f"{attachment['reason']}"
                        )
        except Exception as error:
            st.error(
                "Kontextdokumente konnten nicht gelesen werden: "
                f"{error}"
            )
            profile_context = ""
            candidate_insight_context = ""
            attachments = []
    else:
        st.caption(
            "Kontextdokumente sind optional. Ohne Upload nutzt CareerHub "
            "das aktive Profil und den Company-Match-Kontext."
        )

    company_key = _company_match_key(
        selected_company_match,
        profile_tags,
        candidate_insight_context,
    )
    cached_letters = st.session_state.setdefault(
        "company_initiative_letter_cache",
        {},
    )

    if st.button(
        "Initiativbewerbung erzeugen",
        key=f"generate_company_initiative_{company_key}",
    ):
        if not profile_tags:
            st.warning(
                "Keine aktiven Profilskills gefunden. "
                "Bitte zuerst ein Profil erstellen oder laden."
            )
            return

        if company_key in cached_letters:
            initiative_letter = cached_letters[company_key]
        else:
            try:
                with st.spinner(
                    "Qwen erstellt die Initiativbewerbung..."
                ):
                    initiative_letter = generate_company_initiative_letter(
                        company_name=company_name,
                        profile_tags=sorted(profile_tags),
                        company_context=_company_initiative_context(
                            selected_company_match
                        ),
                        profile_context=candidate_insight_context,
                    )
            except Exception as error:
                st.error(
                    "Initiativbewerbung konnte nicht erzeugt werden. "
                    f"Ollama/LLM ist eventuell nicht verfuegbar: {error}"
                )
                debug = last_cover_letter_debug()

                if debug:
                    st.code(
                        debug,
                        language="text",
                    )

                return

            cached_letters[company_key] = initiative_letter

        if not initiative_letter.strip():
            st.error(
                "Ollama hat keine Initiativbewerbung zurueckgegeben."
            )
            debug = last_cover_letter_debug()

            if debug:
                st.code(
                    debug,
                    language="text",
                )

            cached_letters.pop(
                company_key,
                None,
            )
            return

        st.session_state[
            "generated_company_initiative_letter"
        ] = initiative_letter
        st.session_state[
            "generated_company_initiative_company_key"
        ] = company_key
        st.success(
            f"Initiativbewerbung erzeugt: {len(initiative_letter)} Zeichen"
        )

    generated_letter = st.session_state.get(
        "generated_company_initiative_letter"
    )

    if (
        st.session_state.get("generated_company_initiative_company_key")
        != company_key
    ):
        generated_letter = None

    if generated_letter:
        st.text_area(
            "Initiativbewerbung",
            generated_letter,
            height=360,
        )
        _render_company_application_export(
            selected_company_match=selected_company_match,
            initiative_letter=generated_letter,
            profile_tags=profile_tags,
            candidate_insight_context=candidate_insight_context,
            attachments=attachments,
        )


def render_application_tab():
    st.subheader("Bewerbungsmappe")

    profile_tags = st.session_state.get(
        "profile_tags",
        set(),
    )
    selected_company_match = st.session_state.get(
        "selected_company_match"
    )

    if selected_company_match:
        company = getattr(
            selected_company_match,
            "company",
            None,
        )
        company_name = getattr(
            company,
            "name",
            "das vorgemerkte Unternehmen",
        )
        st.info(
            f"Es ist ein Company Match vorgemerkt: {company_name}. "
            "Du kannst daraus optional eine Initiativbewerbung erzeugen."
        )

    _render_company_initiative_section(
        selected_company_match,
        profile_tags,
    )

    selected_job = st.session_state.get(
        "selected_application_job"
    )

    if not selected_job:
        st.info(
            "Bitte zunächst einen Job im Tab "
            "'Jobs matchen' auswählen."
        )
        return

    st.success(
        "Job für Bewerbungsmappe ausgewählt."
    )

    st.write(
        f"**Position:** {selected_job.title}"
    )

    st.write(
        f"**Unternehmen:** {_company_display(selected_job)}"
    )

    source_name = _source_display(selected_job)

    if source_name:
        st.caption(
            f"Quelle: {source_name}"
        )

    clean_description = _clean_description(
        selected_job
    )

    with st.expander(
        "Stellenbeschreibung anzeigen",
        expanded=False,
    ):
        st.write(
            clean_description[:3000]
        )

    st.markdown("### Kontext für das Anschreiben")

    context_files = st.file_uploader(
        "CV, Projektübersicht, Arbeitszeugnisse, Zertifikate oder Bewerbungsmappe hochladen",
        type=["pdf", "txt", "docx"],
        accept_multiple_files=True,
        key="application_context_uploads",
    )

    profile_context = ""

    if context_files:
        try:
            profile_context = _application_context_text(
                context_files
            )
            st.success(
                f"{len(context_files)} Kontextdatei(en) geladen, "
                f"{len(profile_context)} Zeichen extrahiert."
            )

            with st.expander(
                "Extrahierten Kontext anzeigen",
                expanded=False,
            ):
                st.text_area(
                    "Kontext",
                    profile_context[:6000],
                    height=260,
                )

        except Exception as error:
            st.error(
                f"Kontext konnte nicht gelesen werden: {error}"
            )
    else:
        st.info(
            "Optional: Lade Bewerbungsunterlagen hoch. "
            "Nur dieser Kontext wird für das Anschreiben verwendet."
        )

    attachments = []

    try:
        attachments = _application_attachments(
            context_files
        )
    except Exception as error:
        st.error(
            f"Anlagen konnten nicht ausgewertet werden: {error}"
        )

    if attachments:
        with st.expander(
            "Erkannte Anlagen",
            expanded=False,
        ):
            for attachment in attachments:
                st.write(
                    f"- {attachment['name']} - "
                    f"{attachment['reason']}"
                )

    has_resume_attachment = _has_resume_attachment(
        attachments
    )

    if has_resume_attachment:
        st.info(
            "Ein Lebenslauf wurde in den Anlagen erkannt. "
            "Die HTML-Mappe verzichtet deshalb auf den "
            "zusaetzlichen KI-Lebenslauf."
        )

    profile_summary = _profile_summary(
        profile_tags
    )

    job_tags = _job_skill_analysis(
        selected_job,
        clean_description,
    )

    matched_tags, missing_tags = compare_profile_to_job(
        profile_tags,
        job_tags,
    )

    st.markdown("### Profil-Skills")

    if profile_tags:
        for tag in sorted(profile_tags):
            st.write(
                f"✓ {label_tag(tag)}"
            )
    else:
        st.warning(
            "Keine Profil-Skills gefunden. "
            "Bitte zuerst ein Profil erstellen oder laden."
        )

    st.markdown("### Match-Analyse")

    if job_tags:
        match_count = len(matched_tags)
        total_count = len(job_tags)
        match_percentage = round(
            match_count / total_count * 100
        )

        st.success(
            f"Skill-Match: {match_count}/{total_count} "
            f"Anforderungen erfüllt ({match_percentage}%)"
        )

        if matched_tags:
            st.markdown("#### Übereinstimmungen")

            for tag in sorted(matched_tags):
                st.write(
                    f"✓ {label_tag(tag)}"
                )

        if missing_tags:
            st.markdown("#### Fehlende Anforderungen")

            for tag in sorted(missing_tags):
                st.write(
                    f"• {label_tag(tag)}"
                )
    else:
        st.info(
            "Aus der Stellenbeschreibung konnten noch "
            "keine Anforderungen extrahiert werden."
        )

    if st.button(
        "Anschreiben generieren"
    ):
        if not profile_context.strip():
            st.warning(
                "Es wurden keine Kontextdateien hochgeladen. "
                "Das Anschreiben nutzt nur Skills und Stellenbeschreibung."
            )

        cover_letter_key = _cover_letter_key(
            selected_job,
            profile_tags,
            profile_context,
        )

        profile_tags_list = sorted(
            profile_tags
        )

        cached_cover_letters = st.session_state.setdefault(
            "cover_letter_cache",
            {},
        )

        if cover_letter_key in cached_cover_letters:
            cover_letter = cached_cover_letters[
                cover_letter_key
            ]
        else:
            with st.spinner(
                "Qwen erstellt das Anschreiben..."
            ):
                cover_letter = generate_cover_letter(
                    job_title=selected_job.title,
                    company=selected_job.company,
                    profile_tags=profile_tags_list,
                    job_description=clean_description,
                    profile_context=profile_context,
                )

            cached_cover_letters[
                cover_letter_key
            ] = cover_letter

        if not cover_letter.strip():
            st.error(
                "Ollama hat kein Anschreiben zurückgegeben. "
                "Details stehen in der Konsole."
            )
            st.code(
                last_cover_letter_debug()
                or "Keine Debugdetails verfügbar.",
                language="text",
            )
            st.caption(
                "Logdatei: logs/careerhub_application.log"
            )
            cached_cover_letters.pop(
                cover_letter_key,
                None,
            )
            return

        st.session_state[
            "generated_cover_letter"
        ] = cover_letter
        st.session_state[
            "generated_cover_letter_job_key"
        ] = _job_key(selected_job)

        st.success(
            f"Anschreiben erzeugt: {len(cover_letter)} Zeichen"
        )

    if st.button(
        "Kontextbezogenen Lebenslauf generieren",
        disabled=has_resume_attachment,
    ):
        if not profile_context.strip():
            st.warning(
                "Es wurden keine Kontextdateien hochgeladen. "
                "Der Lebenslauf nutzt nur Skills und Stellenbeschreibung."
            )

        resume_key = _resume_key(
            selected_job,
            profile_tags,
            profile_context,
        )

        cached_resumes = st.session_state.setdefault(
            "context_resume_cache",
            {},
        )

        if resume_key in cached_resumes:
            context_resume = cached_resumes[resume_key]
        else:
            with st.spinner(
                "Qwen erstellt den kontextbezogenen Lebenslauf..."
            ):
                context_resume = generate_context_resume(
                    job_title=selected_job.title,
                    company=selected_job.company,
                    profile_tags=sorted(profile_tags),
                    job_description=clean_description,
                    profile_context=profile_context,
                )

            cached_resumes[resume_key] = context_resume

        if not context_resume.strip():
            st.error(
                "Ollama hat keinen Lebenslauf zurueckgegeben."
            )
            st.code(
                last_cover_letter_debug()
                or "Keine Debugdetails verfuegbar.",
                language="text",
            )
            cached_resumes.pop(
                resume_key,
                None,
            )
            return

        st.session_state[
            "generated_context_resume"
        ] = context_resume
        st.session_state[
            "generated_context_resume_job_key"
        ] = _job_key(selected_job)

        st.success(
            f"Lebenslauf erzeugt: {len(context_resume)} Zeichen"
        )

    generated_cover_letter = st.session_state.get(
        "generated_cover_letter"
    )

    generated_context_resume = st.session_state.get(
        "generated_context_resume"
    )

    if (
        st.session_state.get("generated_cover_letter_job_key")
        != _job_key(selected_job)
    ):
        generated_cover_letter = None

    if (
        st.session_state.get("generated_context_resume_job_key")
        != _job_key(selected_job)
    ):
        generated_context_resume = None

    if generated_cover_letter:
        st.markdown("### Generiertes Anschreiben")

        st.text_area(
            "Anschreiben",
            generated_cover_letter,
            height=400,
        )

        st.markdown("### Profilzusammenfassung")

        st.text_area(
            "Profil",
            profile_summary,
            height=250,
        )

        if generated_context_resume and not has_resume_attachment:
            st.markdown("### Kontextbezogener Lebenslauf")

            st.text_area(
                "Lebenslauf",
                generated_context_resume,
                height=320,
            )
        elif has_resume_attachment:
            st.info(
                "Der generierte Lebenslauf wird nicht in die "
                "HTML-Mappe uebernommen, weil bereits ein "
                "Lebenslauf als Anlage enthalten ist."
            )
        else:
            st.info(
                "Optional: Erzeuge den kontextbezogenen Lebenslauf, "
                "damit er in die Bewerbungsmappe uebernommen wird."
            )

        html_content = generate_application_html(
            cover_letter=generated_cover_letter,
            profile_summary=profile_summary,
            profile_tags=sorted(profile_tags),
            job_title=selected_job.title,
            company=selected_job.company,
            matched_tags=sorted(matched_tags),
            missing_tags=sorted(missing_tags),
            job_required_tags=sorted(job_tags),
            context_resume=(
                ""
                if has_resume_attachment
                else generated_context_resume or ""
            ),
            attachments=attachments,
        )

        st.download_button(
            label="Bewerbungsmappe als HTML inkl. Anlagen herunterladen",
            data=html_content,
            file_name="bewerbungsmappe.html",
            mime="text/html",
        )

        final_pdf_content = None

        if is_html_pdf_renderer_available():
            final_pdf_content = _application_pdf_bytes(
                html_content,
                attachments,
            )

        if final_pdf_content:
            st.download_button(
                label="Finale Bewerbungsmappe als PDF herunterladen",
                data=final_pdf_content,
                file_name="bewerbungsmappe.pdf",
                mime="application/pdf",
            )
        else:
            st.info(
                "Fuer automatische PDF-Erzeugung bitte WeasyPrint oder "
                "wkhtmltopdf installieren. Alternativ die HTML-Datei "
                "im Browser oeffnen und als PDF drucken."
            )
            st.caption(
                _pdf_renderer_status_text()
            )

        zip_content = _application_zip_bytes(
            html_content,
            attachments,
        )

        st.download_button(
            label="Exportpaket als ZIP herunterladen",
            data=zip_content,
            file_name="bewerbungsmappe.zip",
            mime="application/zip",
        )
    else:
        st.info(
            "Erzeuge zuerst ein Anschreiben, "
            "danach steht der HTML-Download bereit."
        )
