from pathlib import Path

from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.company_recommendation_service import (
    deactivate_tracked_company,
    get_recommended_companies,
    get_tracked_companies,
    track_recommended_company,
)
from jobagent.services.companyhub_db_service import get_connection


def _recommended_company(name: str):
    return next(
        company
        for company in get_recommended_companies()
        if company.name == name
    )


def test_companyhub_seed_dashboard_controls_are_present():
    source = Path(
        "src/jobagent/ui/company_tab.py"
    ).read_text(
        encoding="utf-8"
    )

    assert "CompanyHub" in source
    assert "Empfohlene Unternehmen" in source
    assert "Meine Unternehmen" in source
    assert "Beobachten" in source
    assert "Nicht mehr beobachten" in source
    assert "Quellen abrufen" in source
    assert "Alle Dokumente anzeigen" in source
    assert "Evidenz erzeugen" in source
    assert "Knowledge Draft erzeugen" in source
    assert "Knowledge Draft prüfen / verbessern" in source
    assert "Knowledge Draft:" in source
    assert "Pipeline Inspector" in source
    assert "inspect_company" in source
    assert "Clean Text anzeigen" in source
    assert "clean_text_lengths" in source
    assert "Ollama Modell" in source
    assert "companyhub_ollama_model" in source
    assert "_available_ollama_models" in source
    assert "OllamaClient" in source
    assert "default_model=selected_ollama_model" in source
    assert "build_company_knowledge" in source
    assert "review_company_knowledge_draft" in source
    assert "load_latest_company_knowledge_draft" in source
    assert "analyze_company" in source
    assert "companyhub_analysis_summary" in source
    assert "companyhub_analysis_warning" in source
    assert "Dokumente:" in source
    assert "Evidence:" in source
    assert "Canonical Concepts" in source
    assert "Profil-Match berechnen" in source
    assert "Company Match:" in source
    assert "match_company_to_profile" in source
    assert "load_latest_company_profile_match" in source
    assert "Mission Keywords" in source
    assert "Business Domains" in source
    assert "Concept Statistics" in source
    assert "concept_types" in source
    assert "unknown_concepts" in source
    assert "extract_company_concepts" in source
    assert "canonicalize_company_concepts" in source
    assert "list_company_evidence" in source
    assert "Vorschau:" in source
    assert "fetch_company_with_summary" in source
    assert "list_documents" in source
    assert "get_recommended_companies" in source
    assert "track_recommended_company" in source
    assert "deactivate_tracked_company" in source


def test_track_recommended_company_creates_company_and_tracking(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    recommended = _recommended_company(
        "Dataport"
    )

    tracked = track_recommended_company(
        recommended,
        "profile-123",
        repository=repository,
    )

    companies = repository.list_companies()
    tracked_companies = get_tracked_companies(
        "profile-123",
        repository=repository,
    )

    assert tracked["active"] == 1
    assert len(companies) == 1
    assert companies[0].name == "Dataport"
    assert len(tracked_companies) == 1
    assert tracked_companies[0]["name"] == "Dataport"
    assert tracked_companies[0]["priority"] == recommended.priority


def test_tracking_recommended_company_twice_does_not_duplicate(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    recommended = _recommended_company(
        "KWS"
    )

    first = track_recommended_company(
        recommended,
        "profile-123",
        repository=repository,
    )
    second = track_recommended_company(
        recommended,
        "profile-123",
        repository=repository,
    )

    with get_connection(repository.db_path) as connection:
        company_count = connection.execute(
            "SELECT COUNT(*) FROM companies"
        ).fetchone()[0]
        tracked_count = connection.execute(
            "SELECT COUNT(*) FROM tracked_companies"
        ).fetchone()[0]

    assert first["id"] == second["id"]
    assert company_count == 1
    assert tracked_count == 1


def test_deactivate_tracked_company_keeps_row_inactive(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    recommended = _recommended_company(
        "Amprion"
    )
    tracked = track_recommended_company(
        recommended,
        "profile-123",
        repository=repository,
    )

    deactivated = deactivate_tracked_company(
        tracked["company_id"],
        "profile-123",
        repository=repository,
    )

    active_tracked = get_tracked_companies(
        "profile-123",
        repository=repository,
    )
    with get_connection(repository.db_path) as connection:
        row = connection.execute(
            """
            SELECT active
            FROM tracked_companies
            WHERE company_id = ? AND profile_fingerprint = ?
            """,
            (
                tracked["company_id"],
                "profile-123",
            ),
        ).fetchone()

    assert deactivated["active"] == 0
    assert active_tracked == []
    assert row["active"] == 0
