from jobagent.models.company_source import CompanySource
from jobagent.repositories.company_repository import CompanyRepository


def _repository(repository: CompanyRepository | None = None) -> CompanyRepository:
    return repository or CompanyRepository()


def add_company_source(
    company_id: int,
    source_type,
    url: str,
    title: str,
    description: str | None = None,
    enabled: bool = True,
    priority: int = 3,
    notes: str | None = None,
    repository: CompanyRepository | None = None,
) -> CompanySource:
    return _repository(
        repository
    ).add_company_source(
        company_id=company_id,
        source_type=source_type,
        url=url,
        title=title,
        description=description,
        enabled=enabled,
        priority=priority,
        notes=notes,
    )


def ensure_company_sources(
    company_id: int,
    source_definitions: list[dict],
    repository: CompanyRepository | None = None,
) -> list[CompanySource]:
    repo = _repository(
        repository
    )

    return [
        repo.add_company_source(
            company_id=company_id,
            source_type=definition["source_type"],
            url=definition["url"],
            title=definition["title"],
            description=definition.get("description"),
            enabled=definition.get("enabled", True),
            priority=definition.get("priority", 3),
            notes=definition.get("notes"),
        )
        for definition in source_definitions
    ]


def list_company_sources(
    company_id: int,
    include_disabled: bool = True,
    repository: CompanyRepository | None = None,
) -> list[CompanySource]:
    return _repository(
        repository
    ).list_company_sources(
        company_id=company_id,
        include_disabled=include_disabled,
    )


def update_company_source(
    source_id: int,
    repository: CompanyRepository | None = None,
    **fields,
) -> CompanySource | None:
    return _repository(
        repository
    ).update_company_source(
        source_id,
        **fields,
    )


def delete_company_source(
    source_id: int,
    repository: CompanyRepository | None = None,
) -> None:
    _repository(
        repository
    ).delete_company_source(
        source_id
    )


def enable_company_source(
    source_id: int,
    repository: CompanyRepository | None = None,
) -> CompanySource | None:
    return _repository(
        repository
    ).enable_company_source(
        source_id
    )


def disable_company_source(
    source_id: int,
    repository: CompanyRepository | None = None,
) -> CompanySource | None:
    return _repository(
        repository
    ).disable_company_source(
        source_id
    )


def load_latest_document(
    source_id: int,
    repository: CompanyRepository | None = None,
):
    return _repository(
        repository
    ).load_latest_document(
        source_id
    )


def list_documents(
    company_id: int,
    repository: CompanyRepository | None = None,
):
    return _repository(
        repository
    ).list_documents(
        company_id
    )
