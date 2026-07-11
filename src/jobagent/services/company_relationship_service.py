from jobagent.models.company_relationship import CompanyRelationship
from jobagent.repositories.company_repository import CompanyRepository


def _repository(repository: CompanyRepository | None = None) -> CompanyRepository:
    return repository or CompanyRepository()


def add_company_relationship(
    company_id: int,
    related_company_name: str,
    relationship_type,
    repository: CompanyRepository | None = None,
    **fields,
) -> CompanyRelationship:
    return _repository(
        repository
    ).add_company_relationship(
        company_id=company_id,
        related_company_name=related_company_name,
        relationship_type=relationship_type,
        **fields,
    )


def upsert_company_relationship(
    company_id: int,
    related_company_name: str,
    relationship_type,
    repository: CompanyRepository | None = None,
    **fields,
) -> CompanyRelationship:
    return _repository(
        repository
    ).upsert_company_relationship(
        company_id=company_id,
        related_company_name=related_company_name,
        relationship_type=relationship_type,
        **fields,
    )


def list_company_relationships(
    company_id: int,
    include_inactive: bool = False,
    repository: CompanyRepository | None = None,
) -> list[CompanyRelationship]:
    return _repository(
        repository
    ).list_company_relationships(
        company_id=company_id,
        include_inactive=include_inactive,
    )


def get_company_relationships_by_type(
    company_id: int,
    relationship_type,
    include_inactive: bool = False,
    repository: CompanyRepository | None = None,
) -> list[CompanyRelationship]:
    return _repository(
        repository
    ).get_company_relationships_by_type(
        company_id=company_id,
        relationship_type=relationship_type,
        include_inactive=include_inactive,
    )


def deactivate_company_relationship(
    relationship_id: int,
    repository: CompanyRepository | None = None,
) -> CompanyRelationship | None:
    return _repository(
        repository
    ).deactivate_company_relationship(
        relationship_id
    )
