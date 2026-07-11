from jobagent.services.application_html_service import (
    generate_application_html,
)
from jobagent.services.application_pdf_service import (
    prepare_html_for_pdf,
)


def test_application_html_layout_contains_print_structure():
    html = generate_application_html(
        cover_letter=(
            "Sehr geehrte Damen und Herren,\n\n"
            + "Dies ist ein langer Layout-Testabsatz. " * 80
        ),
        profile_summary="Profilzusammenfassung. " * 40,
        profile_tags=[
            f"Skill {index}"
            for index in range(1, 31)
        ],
        job_title="Business Transformation Lead",
        company="Example GmbH",
        matched_tags=[
            "project_management",
            "change_management",
        ],
        missing_tags=[
            "governance",
        ],
        job_required_tags=[
            "project_management",
            "change_management",
            "governance",
        ],
        context_resume="Lebenslaufabschnitt. " * 80,
        attachments=[
            {
                "name": "Lebenslauf.pdf",
                "archive_name": "Lebenslauf.pdf",
                "reason": "Lebenslauf erkannt.",
                "bytes": b"%PDF-1.4",
                "kind": "resume",
            },
            {
                "name": "CareerHub Status.pdf",
                "archive_name": "CareerHub_Status.pdf",
                "reason": "Projektunterlage erkannt.",
                "bytes": b"%PDF-1.4",
                "kind": "evidence",
            },
        ],
    )

    assert "@page" in html
    assert "letter-text" in html
    assert "section-block" in html
    assert "attachments-page" in html
    assert '<ol class="attachments">' in html
    assert 'class="attachment-item"' in html


def test_prepare_html_for_pdf_keeps_layout_css():
    html = generate_application_html(
        cover_letter="Kurzanschreiben",
        profile_summary="Kurzprofil",
        profile_tags=[],
        job_title="Position",
        company=None,
        attachments=[],
    )
    prepared = prepare_html_for_pdf(
        html
    )

    assert "@page" in prepared
    assert "attachments-page" in prepared
