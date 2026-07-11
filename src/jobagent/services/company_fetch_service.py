import hashlib
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

from jobagent.models.company_document import CompanyDocument
from jobagent.models.company_source import CompanySource
from jobagent.repositories.company_repository import CompanyRepository


USER_AGENT = "CareerHub CompanyHub Bot"
REQUEST_TIMEOUT_SECONDS = 20
logger = logging.getLogger(__name__)


@dataclass
class FetchSummary:
    checked: int = 0
    successful: int = 0
    failed: int = 0
    updated: int = 0
    unchanged: int = 0
    documents: list[CompanyDocument] | None = None

    def message(self) -> str:
        return (
            f"{self.checked} Quellen geprüft, "
            f"{self.successful} erfolgreich, "
            f"{self.failed} Fehler, "
            f"{self.updated} Dokument(e) aktualisiert, "
            f"{self.unchanged} unverändert."
        )


def _now() -> str:
    return datetime.now(
        timezone.utc
    ).replace(
        microsecond=0
    ).isoformat()


def _repository(repository: CompanyRepository | None = None) -> CompanyRepository:
    return repository or CompanyRepository()


def _content_type_parts(content_type_header: str | None) -> tuple[str | None, str | None]:
    if not content_type_header:
        return None, None

    parts = [
        part.strip()
        for part in content_type_header.split(";")
        if part.strip()
    ]
    mime_type = parts[0].lower() if parts else None
    charset = None

    for part in parts[1:]:
        if part.lower().startswith("charset="):
            charset = part.split(
                "=",
                1,
            )[1].strip()

    return mime_type, charset


def _decode_content(content: bytes, charset: str | None) -> str:
    if not content:
        return ""

    encoding = charset or "utf-8"

    try:
        return content.decode(
            encoding,
            errors="replace",
        )
    except LookupError:
        return content.decode(
            "utf-8",
            errors="replace",
        )


def fetch_source(
    source: CompanySource,
    repository: CompanyRepository | None = None,
) -> CompanyDocument:
    repo = _repository(
        repository
    )
    started_at = time.monotonic()
    fetched_at = _now()
    status_code = 0
    content = b""
    content_type = None
    mime_type = None
    charset = None
    etag = None
    last_modified = None

    logger.info(
        "Downloading company source %s (%s)",
        source.title,
        source.url,
    )

    try:
        response = requests.get(
            source.url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Encoding": "gzip",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        status_code = response.status_code
        content_type = response.headers.get(
            "Content-Type"
        )
        mime_type, charset = _content_type_parts(
            content_type
        )
        charset = charset or response.encoding
        etag = response.headers.get(
            "ETag"
        )
        last_modified = response.headers.get(
            "Last-Modified"
        )

        if 200 <= status_code <= 299:
            content = response.content or b""
    except requests.Timeout:
        logger.info(
            "Download timeout for company source %s",
            source.url,
        )
        status_code = 0
    except requests.RequestException as exc:
        logger.info(
            "Download failed for company source %s: %s",
            source.url,
            exc,
        )
        status_code = 0

    request_duration_ms = int(
        (time.monotonic() - started_at) * 1000
    )
    content_hash = (
        hashlib.sha256(
            content
        ).hexdigest()
        if content
        else None
    )
    document = CompanyDocument(
        company_id=source.company_id,
        source_id=source.id,
        url=source.url,
        title=source.title,
        content_type=content_type,
        mime_type=mime_type,
        charset=charset,
        content_hash=content_hash,
        content_text=_decode_content(
            content,
            charset,
        ),
        status_code=status_code,
        content_size=len(
            content
        ),
        etag=etag,
        last_modified=last_modified,
        fetched_at=fetched_at,
        request_duration_ms=request_duration_ms,
    )

    saved_document = repo.save_company_document(
        document
    )
    logger.info(
        "Downloaded company source %s status=%s size=%s hash=%s",
        source.url,
        saved_document.status_code,
        saved_document.content_size,
        saved_document.content_hash,
    )

    return saved_document


def fetch_company(
    company_id: int,
    repository: CompanyRepository | None = None,
) -> list[CompanyDocument]:
    repo = _repository(
        repository
    )

    return [
        fetch_source(
            source,
            repository=repo,
        )
        for source in repo.list_company_sources(
            company_id,
            include_disabled=False,
        )
    ]


def fetch_company_with_summary(
    company_id: int,
    repository: CompanyRepository | None = None,
) -> FetchSummary:
    repo = _repository(
        repository
    )
    sources = repo.list_company_sources(
        company_id,
        include_disabled=False,
    )
    documents = []
    summary = FetchSummary(
        checked=len(sources),
        documents=documents,
    )

    for source in sources:
        previous = repo.load_latest_document(
            source.id
        )
        document = fetch_source(
            source,
            repository=repo,
        )
        documents.append(
            document
        )

        if document.status_code and 200 <= document.status_code <= 299:
            summary.successful += 1
        else:
            summary.failed += 1

        if document.content_hash and previous and previous.content_hash == document.content_hash:
            summary.unchanged += 1
        elif document.content_hash:
            summary.updated += 1

    return summary


def fetch_all_sources(
    repository: CompanyRepository | None = None,
) -> list[CompanyDocument]:
    repo = _repository(
        repository
    )
    documents = []

    for company in repo.list_companies():
        documents.extend(
            fetch_company(
                company.id,
                repository=repo,
            )
        )

    return documents
