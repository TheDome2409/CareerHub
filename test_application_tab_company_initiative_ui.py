from pathlib import Path


APPLICATION_TAB = Path("src/jobagent/ui/application_tab.py")


def _source() -> str:
    return APPLICATION_TAB.read_text(
        encoding="utf-8"
    )


def test_company_initiative_area_exposes_required_controls():
    source = _source()

    assert "Initiativbewerbung aus Company Match" in source
    assert "Vorgemerktes Company Match" in source
    assert "Company Match Score" in source
    assert "Company Match Report anzeigen" in source
    assert "Moegliche Einsatzfelder" in source
    assert "Strategische Fit-Gruende" in source
    assert "company_initiative_context_uploads" in source
    assert "Initiativbewerbung erzeugen" in source


def test_company_initiative_uses_uploaded_context_in_llm_call():
    source = _source()

    assert "profile_context = _application_context_text" in source
    assert "candidate_insight_context = _candidate_insight_prompt_context" in source
    assert "selected_company_match" in source
    assert "profile_context=candidate_insight_context" in source
    assert "Kein Company Match vorgemerkt" in source


def test_company_initiative_displays_candidate_insights():
    source = _source()

    assert "Candidate Insights anzeigen" in source
    assert "Priorisierte Candidate Insights anzeigen" in source
    assert "extract_candidate_insights" in source
    assert "format_candidate_insights" in source
    assert "rank_candidate_insights" in source
    assert "format_ranked_candidate_insights" in source


def test_company_initiative_exposes_application_package_export():
    source = _source()

    assert "Initiativbewerbungsmappe exportieren" in source
    assert "Anlagen für den Export" in source
    assert "Automatisch erkannte Anlagen" in source
    assert "Weitere Anlagen für die Initiativmappe hochladen" in source
    assert "Anlagenübersicht für den Export" in source
    assert "Finale Bewerbungsmappe als PDF herunterladen" in source
    assert "Exportpaket als ZIP herunterladen" in source
    assert "WeasyPrint oder " in source
    assert "wkhtmltopdf installieren" in source
    assert "PDF-Rendererstatus" in source
    assert "renderer_available" in source
    assert "renderer_path" in source
    assert "pdfkit_import_ok" in source
    assert "_company_application_html" in source
    assert "_application_pdf_bytes" in source
    assert "render_final_application_pdf" in source
    assert "_plain_text_from_html" not in source
    assert "_wrap_pdf_line" not in source
    assert "_application_zip_bytes" in source
    assert "_merge_attachments" in source
    assert "_uploaded_files_as_manual_attachments" in source
    assert "application_kind=\"initiative\"" in source
