from jobagent.models.company_knowledge import CompanyKnowledge
from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.companyhub_db_service import get_connection


def _kws_knowledge() -> CompanyKnowledge:
    return CompanyKnowledge(
        mission="Seeds for sustainable agriculture.",
        vision="Digital and research-driven plant breeding.",
        purpose="Support resilient food systems.",
        core_values=[
            "responsibility",
            "research",
        ],
        business_domains=[
            "agriculture",
            "research",
        ],
        technologies=[
            "SAP",
            "Azure",
            "Power BI",
        ],
        business_units=[
            "Seed production",
            "Research",
        ],
        products=[
            "Seeds",
        ],
        services=[
            "Agricultural advisory",
        ],
        markets=[
            "Europe",
        ],
        locations=[
            "Einbeck",
        ],
        work_models=[
            "hybrid",
        ],
        benefits=[
            "Flexible work",
        ],
        innovation_areas=[
            "Digital Farming",
            "Plant Breeding",
        ],
        critical_infrastructure=False,
        digitalization_maturity=7,
        innovation_score=8,
        sustainability_score=7,
        growth_signals=[
            "Research investment",
        ],
        source_summary="Manual example.",
        culture_summary="Research-oriented culture.",
        leadership_style="Collaborative",
        hiring_strategy="Specialist hiring",
        travel_expectation="Occasional travel",
        language_requirements=[
            "German",
            "English",
        ],
        notes="KWS example profile.",
        confidence=0.85,
        created_at="2026-06-28T12:00:00+00:00",
    )


def test_company_knowledge_save_and_load_roundtrip(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = repository.upsert_company(
        "KWS"
    )
    knowledge = _kws_knowledge()

    saved = repository.save_company_knowledge(
        company.id,
        knowledge,
    )
    loaded = repository.load_company_knowledge(
        company.id
    )

    assert saved.to_dict() == knowledge.to_dict()
    assert loaded.to_dict() == knowledge.to_dict()


def test_company_knowledge_json_fields_roundtrip(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = repository.upsert_company(
        "KWS"
    )

    repository.save_company_knowledge(
        company.id,
        _kws_knowledge(),
    )
    loaded = repository.load_company_knowledge(
        company.id
    )

    assert loaded.business_domains == [
        "agriculture",
        "research",
    ]
    assert loaded.locations == [
        "Einbeck",
    ]
    assert loaded.technologies == [
        "SAP",
        "Azure",
        "Power BI",
    ]
    assert loaded.benefits == [
        "Flexible work",
    ]
    assert loaded.innovation_areas == [
        "Digital Farming",
        "Plant Breeding",
    ]
    assert loaded.growth_signals == [
        "Research investment",
    ]
    assert loaded.products == [
        "Seeds",
    ]
    assert loaded.services == [
        "Agricultural advisory",
    ]
    assert loaded.markets == [
        "Europe",
    ]
    assert loaded.business_units == [
        "Seed production",
        "Research",
    ]
    assert loaded.core_values == [
        "responsibility",
        "research",
    ]


def test_company_knowledge_update_overwrites_without_duplicates(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = repository.upsert_company(
        "KWS"
    )
    repository.save_company_knowledge(
        company.id,
        _kws_knowledge(),
    )
    updated = _kws_knowledge().model_copy(
        update={
            "mission": "Updated mission.",
            "technologies": [
                "SAP",
                "Azure",
            ],
            "created_at": "2026-06-28T13:00:00+00:00",
        }
    )

    repository.update_company_knowledge(
        company.id,
        updated,
    )
    loaded = repository.load_company_knowledge(
        company.id
    )

    with get_connection(repository.db_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM company_profiles WHERE company_id = ?",
            (company.id,),
        ).fetchone()[0]

    assert loaded.mission == "Updated mission."
    assert loaded.technologies == [
        "SAP",
        "Azure",
    ]
    assert count == 1


def test_empty_company_knowledge_is_persistable(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = repository.upsert_company(
        "Empty Co"
    )
    knowledge = CompanyKnowledge(
        created_at="2026-06-28T12:00:00+00:00"
    )

    repository.save_company_knowledge(
        company.id,
        knowledge,
    )
    loaded = repository.load_company_knowledge(
        company.id
    )

    assert loaded.to_dict() == knowledge.to_dict()
    assert loaded.business_domains == []
    assert loaded.technologies == []
    assert loaded.locations == []


def test_multiple_companies_keep_separate_knowledge(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    kws = repository.upsert_company(
        "KWS"
    )
    dataport = repository.upsert_company(
        "Dataport"
    )

    repository.save_company_knowledge(
        kws.id,
        _kws_knowledge(),
    )
    repository.save_company_knowledge(
        dataport.id,
        CompanyKnowledge(
            mission="Public-sector IT.",
            business_domains=[
                "public_sector",
            ],
            technologies=[
                "Cloud",
            ],
            created_at="2026-06-28T12:30:00+00:00",
        ),
    )

    assert repository.load_company_knowledge(kws.id).mission.startswith(
        "Seeds"
    )
    assert repository.load_company_knowledge(dataport.id).business_domains == [
        "public_sector",
    ]


def test_company_knowledge_delete(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = repository.upsert_company(
        "KWS"
    )
    repository.save_company_knowledge(
        company.id,
        _kws_knowledge(),
    )

    repository.delete_company_knowledge(
        company.id
    )

    assert repository.load_company_knowledge(company.id) is None
