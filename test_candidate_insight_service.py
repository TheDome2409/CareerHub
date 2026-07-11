from jobagent.services.candidate_insight_service import (
    extract_candidate_insights,
    format_candidate_insights,
    normalize_document_text,
)


def test_extract_candidate_insights_finds_projects_and_domains():
    text = """
    CareerHub ist ein eigenes Projekt zur KI-gestuetzten Digitalisierung
    des Bewerbungsprozesses.
    In EDI-Projekten wurden Prozesse analysiert und optimiert.
    Projektarbeit umfasste Koordination, Stakeholder-Abstimmung und
    technische Dokumentation.
    """

    insights = extract_candidate_insights(
        text
    )

    assert any(
        "CareerHub" in item
        for item in insights["key_projects"]
    )
    assert any(
        "EDI" in item
        for item in insights["domain_experience"]
    )
    assert any(
        "Prozesse" in item or "optimiert" in item
        for item in insights["process_improvement_examples"]
    )
    assert any(
        "Digitalisierung" in item
        for item in insights["digitalization_examples"]
    )


def test_extract_candidate_insights_deduplicates_items():
    text = """
    CareerHub ist ein eigenes Projekt.
    CareerHub ist ein eigenes Projekt.
    """

    insights = extract_candidate_insights(
        text
    )

    assert insights["key_projects"] == [
        "CareerHub ist ein eigenes Projekt."
    ]


def test_format_candidate_insights_outputs_short_bullets():
    insights = extract_candidate_insights(
        "CareerHub ist ein eigenes Projekt zur Prozessoptimierung."
    )

    formatted = format_candidate_insights(
        insights
    )

    assert formatted.startswith("Candidate Insights:")
    assert "- CareerHub ist ein eigenes Projekt" in formatted


def test_normalize_document_text_removes_hyphenation():
    normalized = normalize_document_text(
        "Vorbereitung technischer Wirtschaftlichkeits-\n"
        "betrachtungen fuer die Geschaeftsfuehrung."
    )

    assert "Wirtschaftlichkeitsbetrachtungen" in normalized
    assert "Wirtschaftlichkeits-" not in normalized


def test_normalize_document_text_joins_pdf_line_fragments():
    normalized = normalize_document_text(
        "und eigener Produktentwicklung: CareerHub als KI-gestuetzter Prototyp fuer\n"
        "erklaerbare Job-Matches."
    )

    assert (
        "CareerHub als KI-gestuetzter Prototyp fuer erklaerbare Job-Matches."
        in normalized
    )


def test_normalize_document_text_removes_repeated_header_and_pages():
    normalized = normalize_document_text(
        "Alex Beispiel · Bewerbung Example Technologies\n"
        "1\n"
        "CareerHub ist ein eigenes Projekt.\n"
        "Alex Beispiel · Bewerbung Example Technologies\n"
        "2\n"
        "EDI-Prozesse wurden optimiert."
    )

    assert "Alex Beispiel · Bewerbung Example Technologies" not in normalized
    assert "\n1\n" not in normalized
    assert "\n2\n" not in normalized
    assert "CareerHub ist ein eigenes Projekt." in normalized


def test_extract_candidate_insights_detects_explainability():
    insights = extract_candidate_insights(
        "CareerHub nutzt Scoring, Ranking und Explainability."
    )

    assert any(
        "Explainability" in item
        for item in insights["technology_signals"]
    )


def test_extract_candidate_insights_detects_business_it():
    insights = extract_candidate_insights(
        "Business-IT-Schnittstelle mit Entscheidungsvorlagen."
    )

    assert any(
        "Business-IT" in item
        for item in insights["domain_experience"]
    )


def test_extract_candidate_insights_detects_wirtschaftlichkeit():
    insights = extract_candidate_insights(
        "Vorbereitung technischer Entscheidungsvorlagen und "
        "Wirtschaftlichkeitsbetrachtungen fuer die Geschaeftsfuehrung."
    )

    assert any(
        "Wirtschaftlichkeitsbetrachtungen" in item
        for item in insights["key_achievements"]
    )


def test_priority_terms_are_not_displaced_by_early_generic_matches():
    text = """
    Python API SQL Azure Microsoft Automatisierung.
    EDI-Prozesse wurden dokumentiert.
    CareerHub nutzt Scoring, Ranking und Explainability.
    Business-IT-Schnittstelle mit Wirtschaftlichkeitsbetrachtungen.
    """

    insights = extract_candidate_insights(
        text
    )
    formatted = format_candidate_insights(
        insights
    )

    assert "Explainability" in formatted
    assert "Business-IT" in formatted
    assert "Wirtschaftlichkeitsbetrachtungen" in formatted


def test_short_bullets_keep_late_priority_terms_visible():
    text = (
        "Sehr langer Kontext mit vielen vorbereitenden Informationen "
        "ueber technische Projekte, Rollouts, Koordination, Workshops, "
        "Dokumentation, Fachbereichskommunikation und am Ende "
        "Business-IT-Schnittstelle."
    )

    formatted = format_candidate_insights(
        extract_candidate_insights(text)
    )

    assert "Business-IT" in formatted


def test_short_bullets_keep_late_explainability_visible():
    text = (
        "Sehr langer Kontext mit vielen vorbereitenden Informationen "
        "ueber Projektmanagement, Produktentwicklung, Prozessanalyse, "
        "Dokumentation, Fachbereichskommunikation, technische Abstimmung, "
        "Scoring, Ranking und am Ende Explainability."
    )

    formatted = format_candidate_insights(
        extract_candidate_insights(text)
    )

    assert "Explainability" in formatted
