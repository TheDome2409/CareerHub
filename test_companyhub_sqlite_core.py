import sqlite3

from jobagent.repositories.company_repository import (
    CompanyRepository,
    normalize_company_name,
)
from jobagent.services.companyhub_db_service import (
    get_connection,
    initialize_companyhub_db,
)


EXPECTED_TABLES = {
    "companies",
    "company_profiles",
    "tracked_companies",
    "company_sources",
    "company_observations",
    "company_match_results",
    "company_documents",
    "company_relationships",
    "company_evidence",
    "company_knowledge_drafts",
    "company_ground_truth_reviews",
}


def test_initialize_companyhub_db_creates_database_and_tables(tmp_path):
    db_path = tmp_path / "companyhub.db"

    created_path = initialize_companyhub_db(
        db_path
    )

    assert created_path == db_path
    assert db_path.exists()

    with get_connection(db_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()

    table_names = {
        row["name"]
        for row in rows
    }

    assert EXPECTED_TABLES.issubset(
        table_names
    )


def test_companyhub_connection_uses_rows_and_foreign_keys(tmp_path):
    db_path = initialize_companyhub_db(
        tmp_path / "companyhub.db"
    )

    with get_connection(db_path) as connection:
        foreign_keys = connection.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0]
        row = connection.execute(
            "SELECT 1 AS value"
        ).fetchone()

    assert foreign_keys == 1
    assert row["value"] == 1


def test_company_repository_creates_and_lists_company(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )

    company = repository.create_company(
        name="Deutsche Telekom",
        website_url="https://www.telekom.com",
        industry="telecommunications",
    )

    assert company.id is not None
    assert company.normalized_name == "deutsche telekom"
    assert company.website_url == "https://www.telekom.com"

    loaded = repository.get_company_by_id(
        company.id
    )
    by_name = repository.get_company_by_normalized_name(
        " Deutsche   Telekom "
    )
    companies = repository.list_companies()

    assert loaded == company
    assert by_name.id == company.id
    assert len(companies) == 1


def test_company_repository_upsert_prevents_duplicates(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )

    first = repository.upsert_company(
        "DB InfraGO",
        industry="rail",
    )
    second = repository.upsert_company(
        " db   infrago ",
        career_url="https://db.jobs",
    )

    assert first.id == second.id
    assert second.career_url == "https://db.jobs"
    assert len(repository.list_companies()) == 1


def test_company_profile_json_roundtrip(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = repository.upsert_company(
        "Amprion"
    )

    repository.add_company_profile(
        company_id=company.id,
        mission="Stromnetze stabil betreiben.",
        vision="Energiewende ermöglichen.",
        culture_summary="Verantwortung und Technik.",
        technology_summary="KRITIS, Netzbetrieb, Digitalisierung.",
        domains=[
            "energy",
            "kritis",
        ],
        work_models=[
            "hybrid",
        ],
        locations=[
            "Dortmund",
            "Remote",
        ],
        kritis_relevance=True,
        innovation_score=7,
        source_summary="Manual seed.",
    )

    profile = repository.get_latest_company_profile(
        company.id
    )

    assert profile.company_id == company.id
    assert profile.domains == [
        "energy",
        "kritis",
    ]
    assert profile.work_models == [
        "hybrid",
    ]
    assert profile.locations == [
        "Dortmund",
        "Remote",
    ]
    assert profile.kritis_relevance is True
    assert profile.innovation_score == 7


def test_company_tracking_upsert_and_listing(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = repository.upsert_company(
        "Dataport"
    )

    tracked = repository.track_company(
        company.id,
        "profile-123",
        priority=2,
        notes="Public-sector fit",
    )
    updated = repository.track_company(
        company.id,
        "profile-123",
        priority=1,
        notes="Higher priority",
    )
    tracked_companies = repository.list_tracked_companies(
        "profile-123"
    )

    assert tracked["id"] == updated["id"]
    assert updated["priority"] == 1
    assert len(tracked_companies) == 1
    assert tracked_companies[0]["name"] == "Dataport"
    assert tracked_companies[0]["notes"] == "Higher priority"


def test_companyhub_foreign_keys_are_enforced(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )

    try:
        repository.add_company_profile(
            company_id=999,
            mission="Invalid",
        )
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError(
            "Expected foreign key violation for missing company."
        )


def test_normalize_company_name_removes_simple_noise():
    assert normalize_company_name("  KWS  Group! GmbH ") == "kws group gmbh"
    assert normalize_company_name("DB---InfraGO") == "db infrago"
