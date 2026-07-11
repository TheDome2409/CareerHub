from jobagent.models.document_model import (
    Document,
    DocumentBlock,
    DocumentSection,
)
from jobagent.services.application_document_builder import (
    build_application_document,
)
from jobagent.services.document_render_service import (
    render_document_to_html,
)


def test_document_engine_renders_multiple_sections():
    document = Document(
        title="Initiativbewerbung Example Technologies",
        subtitle="Company Match",
        sections=[
            DocumentSection(
                title="Anschreiben",
                kind="cover_letter",
                blocks=[
                    DocumentBlock(
                        kind="paragraph",
                        content="Sehr geehrte Damen und Herren.",
                    )
                ],
            ),
            DocumentSection(
                title="Profil",
                kind="profile",
                page_break_before=True,
                blocks=[
                    DocumentBlock(
                        kind="bullet_list",
                        items=[
                            "Projektmanagement",
                            "Digitalisierung",
                        ],
                    )
                ],
            ),
        ],
    )

    html = render_document_to_html(
        document
    )

    assert "Initiativbewerbung Example Technologies" in html
    assert "Company Match" in html
    assert "Sehr geehrte Damen und Herren." in html
    assert "document-page-break-before" in html
    assert "Projektmanagement" in html


def test_document_engine_footer_is_not_rendered_as_own_section():
    document = Document(
        title="Bewerbungsmappe",
        metadata={
            "footer_note": "Erstellt mit CareerHub",
        },
        sections=[
            DocumentSection(
                title="Profil",
                kind="profile",
                blocks=[
                    DocumentBlock(
                        kind="paragraph",
                        content="Kurzprofil",
                    )
                ],
            )
        ],
    )

    html = render_document_to_html(
        document
    )

    assert '<footer class="document-footer">Erstellt mit CareerHub</footer>' in html
    assert "<section" in html
    assert "document-section-footer" not in html


def test_document_engine_renders_attachment_overview_once():
    document = Document(
        title="Bewerbungsmappe",
        sections=[
            DocumentSection(
                title="Anlagen",
                kind="attachments",
                blocks=[
                    DocumentBlock(
                        kind="attachment_overview",
                        items=[
                            {
                                "title": "Zwischenzeugnis Example Foods GmbH",
                            }
                        ],
                    ),
                    DocumentBlock(
                        kind="attachment_overview",
                        items=[
                            {
                                "title": "Doppelte Anlagenliste",
                            }
                        ],
                    ),
                ],
            )
        ],
    )

    html = render_document_to_html(
        document
    )

    assert (
        html.count('<div class="document-block document-block-attachment_overview">')
        == 1
    )
    assert "Zwischenzeugnis Example Foods GmbH" in html
    assert "Doppelte Anlagenliste" not in html


def test_document_engine_skips_empty_sections():
    document = Document(
        title="Bewerbungsmappe",
        sections=[
            DocumentSection(
                title="Leerer Abschnitt",
                kind="empty",
                blocks=[
                    DocumentBlock(
                        kind="paragraph",
                        content="",
                    )
                ],
            ),
            DocumentSection(
                title="Profil",
                kind="profile",
                blocks=[
                    DocumentBlock(
                        kind="paragraph",
                        content="Kurzprofil",
                    )
                ],
            ),
        ],
    )

    html = render_document_to_html(
        document
    )

    assert "Leerer Abschnitt" not in html
    assert "Kurzprofil" in html


def test_application_document_builder_uses_curated_attachment_overview():
    document = build_application_document(
        title="Initiative Example Technologies",
        cover_letter="Anschreiben",
        profile_summary="Profil",
        profile_tags=[
            "project_management",
        ],
        attachments=[
            {
                "name": "Anlage_1.pdf",
                "reason": "Generische Anlage.",
            }
        ],
        curated_attachment_overview=[
            {
                "title": "IHK Pruefungszeugnis Fachinformatiker",
                "description": "Formaler Abschluss.",
            }
        ],
        include_attachment_fallback=True,
    )
    html = render_document_to_html(
        document
    )

    assert (
        html.count('<div class="document-block document-block-attachment_overview">')
        == 1
    )
    assert "IHK Pruefungszeugnis Fachinformatiker" in html
    assert "Generische Anlage" not in html
    assert "Es wurde noch keine kuratierte" not in html


def test_application_document_builder_fallback_only_without_curated_overview():
    document = build_application_document(
        title="Initiative Example Technologies",
        cover_letter="Anschreiben",
        profile_summary="Profil",
        profile_tags=[
            "project_management",
        ],
        attachments=[],
        include_attachment_fallback=True,
    )
    html = render_document_to_html(
        document
    )

    assert "Anlagen werden separat beigefuegt" in html
    assert (
        html.count('<div class="document-block document-block-attachment_overview">')
        == 1
    )
