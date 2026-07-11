from jobagent.models.company_relationship import (
    CompanyRelationship,
    RelationshipDirection,
    RelationshipType,
)
from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.company_relationship_service import (
    deactivate_company_relationship,
    get_company_relationships_by_type,
    list_company_relationships,
    upsert_company_relationship,
)
from jobagent.services.companyhub_db_service import get_connection


def test_company_relationship_model_can_be_created():
    relationship = CompanyRelationship(
        company_id=1,
        related_company_name="Schwarz Gruppe",
        relationship_type=RelationshipType.PARENT_COMPANY,
        direction=RelationshipDirection.OUTGOING,
        confidence=0.9,
        source="manual",
        observed_at="2026-01-01T00:00:00+00:00",
        created_at="2026-01-01T00:00:00+00:00",
    )

    assert relationship.relationship_type == RelationshipType.PARENT_COMPANY
    assert relationship.direction == RelationshipDirection.OUTGOING
    assert relationship.active is True


def test_company_relationship_table_is_created(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )

    with get_connection(repository.db_path) as connection:
        row = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'company_relationships'
            """
        ).fetchone()

    assert row["name"] == "company_relationships"


def test_company_relationship_can_be_saved_and_listed(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = repository.upsert_company(
        "DB InfraGO"
    )

    relationship = upsert_company_relationship(
        company.id,
        "Deutsche Bahn",
        RelationshipType.PARENT_COMPANY,
        direction=RelationshipDirection.OUTGOING,
        confidence=0.95,
        source="manual",
        evidence_text="DB InfraGO ist Teil des Deutsche-Bahn-Konzerns.",
        repository=repository,
    )
    relationships = list_company_relationships(
        company.id,
        repository=repository,
    )

    assert relationship.id is not None
    assert len(relationships) == 1
    assert relationships[0].related_company_name == "Deutsche Bahn"
    assert relationships[0].relationship_type == "parent_company"


def test_company_relationship_upsert_prevents_duplicates(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = repository.upsert_company(
        "Lidl"
    )

    first = upsert_company_relationship(
        company.id,
        "Schwarz Gruppe",
        RelationshipType.GROUP_COMPANY,
        source="manual",
        confidence=0.8,
        repository=repository,
    )
    second = upsert_company_relationship(
        company.id,
        " schwarz-gruppe ",
        RelationshipType.GROUP_COMPANY,
        source="manual",
        confidence=0.9,
        evidence_text="Aktualisierte Evidenz.",
        repository=repository,
    )
    relationships = list_company_relationships(
        company.id,
        repository=repository,
    )

    assert first.id == second.id
    assert len(relationships) == 1
    assert relationships[0].confidence == 0.9
    assert relationships[0].evidence_text == "Aktualisierte Evidenz."


def test_deactivate_company_relationship(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = repository.upsert_company(
        "Neudorff"
    )
    relationship = upsert_company_relationship(
        company.id,
        "Dr. Paul Lohmann",
        RelationshipType.OTHER,
        confidence=0.4,
        source="manual",
        repository=repository,
    )

    deactivated = deactivate_company_relationship(
        relationship.id,
        repository=repository,
    )

    assert deactivated.active is False
    assert list_company_relationships(
        company.id,
        repository=repository,
    ) == []
    assert len(
        list_company_relationships(
            company.id,
            include_inactive=True,
            repository=repository,
        )
    ) == 1


def test_company_relationships_can_be_filtered_by_type(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = repository.upsert_company(
        "Example"
    )

    upsert_company_relationship(
        company.id,
        "Parent",
        RelationshipType.PARENT_COMPANY,
        repository=repository,
    )
    upsert_company_relationship(
        company.id,
        "Partner",
        RelationshipType.PARTNER,
        repository=repository,
    )

    parent_relationships = get_company_relationships_by_type(
        company.id,
        RelationshipType.PARENT_COMPANY,
        repository=repository,
    )

    assert len(parent_relationships) == 1
    assert parent_relationships[0].related_company_name == "Parent"


def test_company_relationship_self_fk_can_reference_company(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = repository.upsert_company(
        "Former Name GmbH"
    )

    relationship = upsert_company_relationship(
        company.id,
        "Former Name GmbH",
        RelationshipType.FORMER_NAME,
        related_company_id=company.id,
        direction=RelationshipDirection.BIDIRECTIONAL,
        repository=repository,
    )

    assert relationship.related_company_id == company.id
    assert relationship.direction == "bidirectional"
