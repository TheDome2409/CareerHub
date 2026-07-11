from jobagent.models.company import CompanyProfile
from jobagent.models.company_match_result import CompanyMatchResult
from jobagent.services.candidate_insight_ranker import (
    build_candidate_insight_views,
    format_candidate_insight_views,
    format_ranked_candidate_insights,
    rank_candidate_insights,
)


def _synatix_match() -> CompanyMatchResult:
    company = CompanyProfile(
        name="Example Technologies",
        description=(
            "Venture Builder für digitale Geschäftsmodelle, "
            "Produktentwicklung, Softwareentwicklung und KI-Tools."
        ),
        focus_areas=[
            "digitale Geschäftsmodelle",
            "Produktentwicklung",
            "Venture Building",
        ],
        possible_use_cases=[
            "IT-Projektmanagement",
            "technische Produktentwicklung",
            "KI-gestützte Tools wie CareerHub",
        ],
        detected_skills=[
            "digitalization",
            "product development",
            "ai tools",
        ],
        detected_competencies=[
            "digitalization",
            "process_improvement",
        ],
    )

    return CompanyMatchResult(
        company=company,
        total_score=100,
        strategic_fit_score=25,
        reasons=[
            "Strategic Fit: Digitalisierung",
            "Strategic Fit: Produktentwicklung",
            "Strategic Fit: Innovation",
        ],
        application_recommendation="Initiativbewerbung sinnvoll",
    )


def test_rank_candidate_insights_prioritizes_synatix_relevance():
    insights = {
        "key_projects": [
            "CareerHub ist ein KI-gestützter Prototyp für erklärbare Job-Matches.",
            "Generische IT-Dokumentation und Ticketerfassung.",
        ],
        "technology_signals": [
            "CareerHub nutzt Scoring, Ranking und Explainability.",
            "Microsoft Windows und allgemeine IT-Kenntnisse.",
        ],
        "domain_experience": [
            "EDI-Prozesse wurden dokumentiert.",
        ],
        "digitalization_examples": [
            "Eigene Produktentwicklung mit MVP und Prototyping.",
        ],
    }

    ranked = rank_candidate_insights(
        insights,
        company_match=_synatix_match(),
        company_match_report=(
            "Example Technologies verbindet Produktentwicklung, digitale "
            "Geschäftsmodelle und KI-gestützte Tools."
        ),
    )
    top_text = "\n".join(
        item["insight"]
        for item in ranked[:3]
    )

    assert "CareerHub" in top_text
    assert "Produktentwicklung" in top_text
    assert "Generische IT-Dokumentation" not in top_text


def test_rank_candidate_insights_keeps_existing_facts_only():
    insights = {
        "key_projects": [
            "CareerHub ist ein eigenes Produkt- und Lernprojekt.",
        ],
    }

    ranked = rank_candidate_insights(
        insights,
        company_match=_synatix_match(),
    )
    formatted = format_ranked_candidate_insights(
        ranked
    )

    assert "CareerHub ist ein eigenes Produkt- und Lernprojekt." in formatted
    assert "Kunden" not in formatted
    assert "Umsatz" not in formatted


def test_format_ranked_candidate_insights_numbers_top_items():
    ranked = [
        {
            "insight": "CareerHub nutzt Explainability.",
            "score": 90,
            "field": "technology_signals",
        },
        {
            "insight": "EDI-Prozesse wurden dokumentiert.",
            "score": 30,
            "field": "domain_experience",
        },
    ]

    formatted = format_ranked_candidate_insights(
        ranked
    )

    assert formatted.startswith("Top Candidate Insights:")
    assert "1. CareerHub nutzt Explainability." in formatted
    assert "2. EDI-Prozesse wurden dokumentiert." in formatted


def test_candidate_insight_views_turn_fragments_into_summary():
    ranked = [
        {
            "insight": (
                "...entwickle ich privat CareerHub: eine KI-gestützte "
                "Plattform mit OCR, LLM-Integration, Ranking und Explainability."
            ),
            "score": 120,
            "field": "key_projects",
        },
        {
            "insight": (
                "...Protection Business-IT-Schnittstelle "
                "Entscheidungsvorlagen, Wirtschaftlichkeitsbetrachtung."
            ),
            "score": 90,
            "field": "key_achievements",
        },
    ]

    views = build_candidate_insight_views(
        ranked
    )
    formatted = format_candidate_insight_views(
        views
    )

    assert views[0].title == "CareerHub - KI-gestützte Produktentwicklung"
    assert "Eigenständige Entwicklung einer Plattform" in views[0].description
    assert "OCR" in views[0].description
    assert "Explainability" in views[0].description
    assert "..." not in formatted
    assert "Protection Business-IT" not in formatted


def test_rank_candidate_insights_filters_internal_feature_lists():
    insights = {
        "technology_signals": [
            "Skill Score, Competency Score, Gesamtbewertung, Ranking.",
            "Unknown Skill Review, Canonicalization, Pipeline und Export.",
        ],
        "key_projects": [
            (
                "CareerHub ist ein eigenständiges Projekt mit "
                "Produktentwicklung und Explainability."
            ),
        ],
        "key_achievements": [
            (
                "Vorbereitung technischer Entscheidungsvorlagen und "
                "Wirtschaftlichkeitsbetrachtungen für die Geschäftsführung."
            ),
        ],
    }

    ranked = rank_candidate_insights(
        insights,
        company_match=_synatix_match(),
    )
    ranked_text = "\n".join(
        item["insight"]
        for item in ranked
    )

    assert "Skill Score" not in ranked_text
    assert "Unknown Skill Review" not in ranked_text
    assert "CareerHub" in ranked_text
    assert "Wirtschaftlichkeitsbetrachtungen" in ranked_text


def test_rank_candidate_insights_prefers_personal_work_over_features():
    insights = {
        "technology_signals": [
            "Scoring Komponenten, Ranking, Import und Export.",
        ],
        "leadership_signals": [
            (
                "Business-IT-Schnittstelle mit Stakeholder-Koordination, "
                "Verantwortung und Entscheidungsvorlagen."
            ),
        ],
        "digitalization_examples": [
            "Digitalisierung von Prozessen mit Fachbereichsabstimmung.",
        ],
    }

    ranked = rank_candidate_insights(
        insights,
        company_match=_synatix_match(),
    )

    assert ranked[0]["insight"].startswith("Business-IT-Schnittstelle")
    assert all(
        "Export" not in item["insight"]
        for item in ranked
    )


def test_candidate_insight_views_use_export_safe_german_text():
    ranked = [
        {
            "insight": (
                "CareerHub ist ein KI-gestuetztes Projekt fuer "
                "digitale Geschaeftsmodelle."
            ),
            "score": 120,
            "field": "key_projects",
        },
        {
            "insight": (
                "Entscheidungsvorlagen fuer entscheidungsfaehige "
                "Geschaeftsfuehrungskontexte."
            ),
            "score": 90,
            "field": "key_achievements",
        },
    ]

    formatted = format_candidate_insight_views(
        build_candidate_insight_views(
            ranked
        )
    )

    assert "KI-gestützte" in formatted
    assert "Eigenständige" in formatted
    assert "Geschäftsführungskontexte" in formatted
    assert "KI-gestuetzte" not in formatted
    assert "Geschaeftsfuehrung" not in formatted
