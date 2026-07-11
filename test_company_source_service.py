from jobagent.models.company_enums import SourceType
from jobagent.models.company_source import CompanySource
from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.company_recommendation_service import (
    get_recommended_companies,
    track_recommended_company,
)
from jobagent.services.company_source_service import (
    add_company_source,
    disable_company_source,
    enable_company_source,
    list_company_sources,
)
from jobagent.services.companyhub_db_service import get_connection


def test_company_source_model_can_be_created():
    source = CompanySource(
        company_id=1,
        source_type=SourceType.COMPANY_WEBSITE,
        url="https://www.dataport.de",
        title="Dataport Website",
        created_at="2026-01-01T00:00:00+00:00",
    )

    assert source.company_id == 1
    assert source.source_type == SourceType.COMPANY_WEBSITE
    assert source.enabled is True
    assert source.priority == 3


def test_multiple_company_sources_are_stored_and_sorted(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = repository.upsert_company(
        "Dataport"
    )

    add_company_source(
        company.id,
        SourceType.CAREER_PAGE,
        "https://www.dataport.de/karriere",
        "Dataport Karriere",
        priority=2,
        repository=repository,
    )
    add_company_source(
        company.id,
        SourceType.COMPANY_WEBSITE,
        "https://www.dataport.de",
        "Dataport Website",
        priority=1,
        repository=repository,
    )

    sources = list_company_sources(
        company.id,
        repository=repository,
    )

    assert [
        source.title
        for source in sources
    ] == [
        "Dataport Website",
        "Dataport Karriere",
    ]


def test_disable_and_enable_company_source(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = repository.upsert_company(
        "KWS"
    )
    source = add_company_source(
        company.id,
        SourceType.COMPANY_WEBSITE,
        "https://www.kws.com",
        "KWS Website",
        repository=repository,
    )

    disabled = disable_company_source(
        source.id,
        repository=repository,
    )
    enabled = enable_company_source(
        source.id,
        repository=repository,
    )

    assert disabled.enabled is False
    assert enabled.enabled is True


def test_company_source_upsert_prevents_duplicates(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = repository.upsert_company(
        "Amprion"
    )

    first = add_company_source(
        company.id,
        SourceType.COMPANY_WEBSITE,
        "https://www.amprion.net",
        "Amprion Website",
        priority=1,
        repository=repository,
    )
    second = add_company_source(
        company.id,
        SourceType.COMPANY_WEBSITE,
        "https://www.amprion.net",
        "Amprion Hauptseite",
        priority=2,
        repository=repository,
    )

    sources = list_company_sources(
        company.id,
        repository=repository,
    )

    assert first.id == second.id
    assert len(sources) == 1
    assert sources[0].title == "Amprion Hauptseite"
    assert sources[0].priority == 2


def test_tracking_seed_company_creates_default_sources(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    dataport = next(
        company
        for company in get_recommended_companies()
        if company.name == "Dataport"
    )

    tracked = track_recommended_company(
        dataport,
        "profile-123",
        repository=repository,
    )
    sources = list_company_sources(
        tracked["company_id"],
        repository=repository,
    )

    assert [
        source.source_type
        for source in sources
    ] == [
        SourceType.COMPANY_WEBSITE,
        SourceType.CAREER_PAGE,
    ]
    assert sources[0].url == "https://www.dataport.de"
    assert sources[1].url == "https://www.dataport.de/karriere"

    with get_connection(repository.db_path) as connection:
        source_count = connection.execute(
            "SELECT COUNT(*) FROM company_sources"
        ).fetchone()[0]

    track_recommended_company(
        dataport,
        "profile-123",
        repository=repository,
    )

    with get_connection(repository.db_path) as connection:
        repeated_source_count = connection.execute(
            "SELECT COUNT(*) FROM company_sources"
        ).fetchone()[0]

    assert repeated_source_count == source_count
