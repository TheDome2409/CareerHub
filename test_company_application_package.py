import zipfile
from io import BytesIO

from jobagent.models.company import CompanyProfile
from jobagent.models.company_match_result import CompanyMatchResult
from jobagent.services.application_html_service import (
    generate_application_html,
)
from jobagent.services.export_text_service import (
    export_label_tag,
    normalize_export_text,
)
from jobagent.services.application_package_service import application_zip_bytes


def _company_match() -> CompanyMatchResult:
    company = CompanyProfile(
        name="Example Technologies",
        description="Venture Builder für digitale Geschäftsmodelle.",
        possible_use_cases=[
            "IT-Projektmanagement",
            "technische Produktentwicklung",
        ],
        focus_areas=[
            "Produktentwicklung",
            "digitale Geschäftsmodelle",
        ],
    )

    return CompanyMatchResult(
        company=company,
        total_score=100,
        reasons=[
            "Strategic Fit: Produktentwicklung",
        ],
        application_recommendation="Initiativbewerbung sinnvoll",
    )


def test_company_application_html_contains_initiative_content():
    match = _company_match()

    html = generate_application_html(
        cover_letter=(
            "Mit gro?em Interesse bewerbe ich mich initiativ bei Example Technologies."
        ),
        profile_summary="Kurzprofil Kandidat",
        profile_tags=[
            "project_management",
            "digitalization",
        ],
        job_title="Initiativbewerbung",
        company=match.company.name,
        attachments=[],
        application_kind="initiative",
        target_label="Bewerbungsziel",
        company_match_report=(
            "Kurzfazit: Example Technologies passt zu Produktentwicklung."
        ),
        possible_use_cases=match.company.possible_use_cases,
        top_candidate_insights=(
            "CareerHub - KI-gestützte Produktentwicklung\n"
            "Eigenständige Entwicklung einer Plattform mit OCR, "
            "LLM-Integration, Ranking und Explainability."
        ),
    )

    assert "Initiativbewerbungsmappe aus Company Match" in html
    assert "Example Technologies" in html
    assert "Mit gro?em Interesse" in html
    assert "Kurzfazit: Example Technologies passt zu Produktentwicklung." in html
    assert "insight-card" in html
    assert "insight-icon" not in html
    assert ">CH<" not in html
    assert "CareerHub - KI-gestützte Produktentwicklung" in html
    assert "Eigenständige Entwicklung einer Plattform" in html
    assert "Mögliche Einsatzfelder" in html
    assert "digitale Geschäftsmodelle" not in html
    assert "Top Candidate Insights:<br>" not in html
    assert "..." not in html
    assert "technische Produktentwicklung" in html


def test_company_application_html_contains_attachment_overview():
    html = generate_application_html(
        cover_letter="Initiativanschreiben",
        profile_summary="Kurzprofil",
        profile_tags=[
            "project_management",
        ],
        job_title="Initiativbewerbung",
        company="Example Technologies",
        attachments=[
            {
                "name": "Application_Beispiel-anlage-seite-3.pdf",
                "archive_name": "Application_Beispiel-anlage-seite-3.pdf",
                "reason": (
                    "CareerHub Projektvorstellung mit Architektur, "
                    "Status und Mehrwert."
                ),
                "bytes": b"%PDF-test",
            },
            {
                "name": "IHK_Pruefungszeugnis_Fachinformatiker_Systemintegration.pdf",
                "archive_name": "IHK_Pruefungszeugnis_Fachinformatiker_Systemintegration.pdf",
                "reason": "IHK Prüfungszeugnis Fachinformatiker Systemintegration.",
                "bytes": b"docx-test",
            },
        ],
        application_kind="initiative",
    )

    assert "Anlagen" in html
    assert "2 Anlage(n) aufgef" in html
    assert "CareerHub-Architektur / Status / Mehrwert" in html
    assert "IHK Prüfungszeugnis Fachinformatiker Systemintegration" in html
    assert "Extrahiert aus" not in html
    assert ">Application_Beispiel-anlage-seite-3.pdf<" not in html
    assert (
        "Originaldatei: Application_Beispiel-anlage-seite-3.pdf"
        not in html
    )
    assert "IHK_Pruefungszeugnis_Fachinformatiker_Systemintegration.pdf" in html


def test_company_application_html_uses_professional_generic_attachment_titles():
    html = generate_application_html(
        cover_letter="Initiativanschreiben",
        profile_summary="Kurzprofil",
        profile_tags=[
            "project_management",
        ],
        job_title="Initiativbewerbung",
        company="Example Technologies",
        attachments=[
            {
                "name": "Arbeitszeugnis_2024.pdf",
                "archive_name": "Arbeitszeugnis_2024.pdf",
                "reason": "Relevantes Zeugnis.",
                "bytes": b"%PDF-test",
            },
            {
                "name": "Zertifikat.pdf",
                "archive_name": "Zertifikat.pdf",
                "reason": "Relevantes Zertifikat.",
                "bytes": b"%PDF-test",
            },
            {
                "name": "Projektunterlage.pdf",
                "archive_name": "Projektunterlage.pdf",
                "reason": "Relevante Projektunterlage.",
                "bytes": b"%PDF-test",
            },
        ],
        application_kind="initiative",
    )

    assert "Zeugnis / Nachweis" not in html
    assert ">Zertifikat<" not in html
    assert ">Projektunterlage<" not in html
    assert "Keine kuratierte Anlagen" not in html
    assert '<section class="page attachments-page">' not in html
    assert "Zeugnis 1" not in html
    assert "Zertifikat 2" not in html
    assert "Projektunterlage 3" not in html


def test_company_application_html_uses_compressed_attachment_preview(monkeypatch):
    monkeypatch.setattr(
        "jobagent.services.application_html_service.pdf_preview_jpeg_data_uri",
        lambda _bytes: "data:image/jpeg;base64,preview",
    )

    html = generate_application_html(
        cover_letter="Initiativanschreiben",
        profile_summary="Kurzprofil",
        profile_tags=[
            "project_management",
        ],
        job_title="Initiativbewerbung",
        company="Example Technologies",
        attachments=[
            {
                "name": "Projekt?bersicht.pdf",
                "archive_name": "Projekt?bersicht.pdf",
                "reason": "Projektunterlage.",
                "bytes": b"%PDF-original-large-file",
            },
        ],
        application_kind="initiative",
    )

    assert "data:image/jpeg;base64,preview" not in html
    assert "data:application/pdf;base64" not in html
    assert "embedded-preview" in html
    assert "PDF-Anhang kann in diesem Browser" not in html


def test_company_application_html_layout_uses_section_page_breaks():
    html = generate_application_html(
        cover_letter="Initiativanschreiben",
        profile_summary="Kurzprofil",
        profile_tags=[
            "project_management",
        ],
        job_title="Initiativbewerbung",
        company="Example Technologies",
        attachments=[
            {
                "name": "Zwischenzeugnis_Example_Foods_GmbH.pdf",
                "archive_name": "Zwischenzeugnis_Example_Foods_GmbH.pdf",
                "reason": (
                    "Zwischenzeugnis Example Foods GebÃ¤ck GmbH. Extrahiert aus "
                    "Example_Technologies_Portfolio.pdf, Seite 3."
                ),
                "bytes": b"%PDF-test",
            },
        ],
        application_kind="initiative",
        top_candidate_insights=(
            "CareerHub - KI-gestÃ¼tzte Produktentwicklung\n"
            "EigenstÃ¤ndige Entwicklung einer Plattform."
        ),
    )

    assert "Zwischenzeugnis Example Foods" in html
    assert "GmbH" in html
    assert "Extrahiert aus Example_Technologies_Portfolio.pdf, Seite 3" not in html
    assert '<section class="page attachments-page">' in html
    assert "break-before: page" in html
    assert html.index("Top Candidate Insights") < html.index("<h1>Anlagen")
    assert "insights-section" in html


def test_company_application_html_suppresses_generated_overview_when_attachment_overview_exists():
    html = generate_application_html(
        cover_letter="Initiativanschreiben",
        profile_summary="Kurzprofil",
        profile_tags=[
            "project_management",
        ],
        job_title="Initiativbewerbung",
        company="Example Technologies",
        attachments=[
            {
                "name": "Example_Technologies_Portfolio-anlage-seite-9.pdf",
                "archive_name": "Example_Technologies_Portfolio-anlage-seite-9.pdf",
                "reason": "Anlagenübersicht.",
                "bytes": b"%PDF-test",
            },
            {
                "name": "Zwischenzeugnis_Example_Foods_GmbH.pdf",
                "archive_name": "Zwischenzeugnis_Example_Foods_GmbH.pdf",
                "reason": "Zwischenzeugnis Example Foods Gebäck GmbH.",
                "bytes": b"%PDF-test",
            },
        ],
        application_kind="initiative",
    )

    assert "Keine kuratierte Anlagen" not in html
    assert "Anlage(n) enthalten" not in html
    assert "Anlage(n) aufgef" not in html
    assert '<section class="page attachments-page">' not in html


def test_company_application_html_generates_single_overview_without_attachment_overview():
    html = generate_application_html(
        cover_letter="Initiativanschreiben",
        profile_summary="Kurzprofil",
        profile_tags=[
            "project_management",
        ],
        job_title="Initiativbewerbung",
        company="Example Technologies",
        attachments=[
            {
                "name": "Zwischenzeugnis_Example_Foods_GmbH.pdf",
                "archive_name": "Zwischenzeugnis_Example_Foods_GmbH.pdf",
                "reason": "Zwischenzeugnis Example Foods Gebäck GmbH.",
                "bytes": b"%PDF-test",
            },
        ],
        application_kind="initiative",
    )

    assert "Keine kuratierte Anlagen" not in html
    assert html.count('class="page attachments-page"') == 1
    assert html.count("<h1>Anlagen") == 1


def test_existing_job_application_html_still_uses_job_structure():
    html = generate_application_html(
        cover_letter="Anschreiben",
        profile_summary="Profil",
        profile_tags=[
            "project_management",
        ],
        job_title="IT Projektleiter",
        company="Muster GmbH",
        matched_tags=[
            "project_management",
        ],
        missing_tags=[],
        job_required_tags=[
            "project_management",
        ],
        attachments=[],
    )

    assert "Automatisch erzeugte Bewerbungsmappe" in html
    assert "<h1>Stelleninformationen</h1>" not in html
    assert "Profil und Kompetenzprofil" in html
    assert "Skill-Match: 1/1 Anforderungen" in html
    assert "IT Projektleiter" in html


def test_application_html_export_uses_professional_pdf_labels():
    html = generate_application_html(
        cover_letter="Anschreiben mit möglicher KI-gestützter Wirkung.",
        profile_summary="Eigenständig berücksichtigt.",
        profile_tags=[
            "project_management",
            "digitalization",
        ],
        job_title="Initiativbewerbung",
        company="Example Technologies",
        attachments=[],
        application_kind="initiative",
        possible_use_cases=[
            "Geschäftsmodelle",
        ],
    )

    assert "✓" not in html
    assert "✅" not in html
    assert "☑" not in html
    assert "möglicher" in html
    assert "KI-gestützter" in html
    assert "Geschäftsmodelle" in html
    assert "berücksichtigt" in html
    assert "Moegliche" not in html
    assert "gestuetzt" not in html
    assert "Geschaeftsmodelle" not in html


def test_export_text_sanitizer_preserves_ascii_and_repairs_mojibake():
    assert export_label_tag("digitalization") == "Digitalisierung"
    assert export_label_tag("data") == "Data / EDI"
    assert normalize_export_text(
        "Mögliche KI-gestützte Geschäftsmodelle für "
        "entscheidungsfähige Unterlagen im Gespräch"
    ) == (
        "Mögliche KI-gestützte Geschäftsmodelle für "
        "entscheidungsfähige Unterlagen im Gespräch"
    )
    assert normalize_export_text(
        "Moegliche KI-gestuetzte Geschaeftsmodelle f?r "
        "entscheidungsfaehige Unterlagen im Gespraech"
    ) == (
        "Moegliche KI-gestuetzte Geschaeftsmodelle f?r "
        "entscheidungsfaehige Unterlagen im Gespraech"
    )
    assert normalize_export_text(
        "MÃ¶gliche Einsatzfelder fÃ¼r Example Technologies"
    ) == "Mögliche Einsatzfelder für Example Technologies"


def test_application_html_export_contains_no_mojibake_skill_labels():
    html = generate_application_html(
        cover_letter="Anschreiben",
        profile_summary="Profil",
        profile_tags=[
            "digitalization",
            "data",
            "leadership",
        ],
        job_title="Initiativbewerbung",
        company="Example Technologies",
        attachments=[],
        application_kind="initiative",
    )

    assert "Digitalisierung" in html
    assert "Data / EDI" in html
    assert "Leadership" in html
    assert "ðŸ" not in html
    assert "âœ" not in html
    assert "💡" not in html
    assert "📊" not in html


def test_company_match_info_does_not_create_empty_final_page():
    html = generate_application_html(
        cover_letter="Initiativanschreiben",
        profile_summary="Kurzprofil",
        profile_tags=[
            "project_management",
        ],
        job_title="Initiativbewerbung",
        company="Example Technologies",
        attachments=[],
        application_kind="initiative",
        target_label="Bewerbungsziel",
    )

    assert "<h1>Company-Match-Informationen</h1>" not in html
    assert "Company-Match-Informationen" not in html
    assert "Bewerbungsziel" in html


def test_company_application_zip_contains_html_and_attachments():
    zip_bytes = application_zip_bytes(
        "<html>Initiativmappe Example Technologies</html>",
        [
            {
                "archive_name": "anlage.pdf",
                "bytes": b"%PDF-test",
            }
        ],
        html_name="Initiative_Example Technologies_CareerHub.html",
    )

    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        names = set(
            archive.namelist()
        )
        html_content = archive.read(
            "Initiative_Example Technologies_CareerHub.html"
        ).decode("utf-8")

    assert "Initiative_Example Technologies_CareerHub.html" in names
    assert "anlagen/anlage.pdf" in names
    assert "Initiativmappe Example Technologies" in html_content
