import hashlib

from jobagent.models.company_enums import SourceType
from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.company_fetch_service import (
    USER_AGENT,
    fetch_company,
    fetch_company_with_summary,
    fetch_source,
)
from jobagent.services.company_source_service import add_company_source


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        content: bytes = b"",
        headers: dict | None = None,
        encoding: str | None = "utf-8",
    ):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}
        self.encoding = encoding


def _source(repository: CompanyRepository, url: str = "https://example.test"):
    company = repository.upsert_company(
        "Example"
    )

    return add_company_source(
        company.id,
        SourceType.COMPANY_WEBSITE,
        url,
        "Example Website",
        repository=repository,
    )


def test_fetch_source_http_200_stores_document_and_hash(tmp_path, monkeypatch):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    source = _source(
        repository
    )
    payload = b"<html>CareerHub</html>"

    def fake_get(url, headers, timeout):
        assert url == source.url
        assert headers["User-Agent"] == USER_AGENT
        assert headers["Accept-Encoding"] == "gzip"
        assert timeout == 20
        return FakeResponse(
            200,
            payload,
            headers={
                "Content-Type": "text/html; charset=utf-8",
                "ETag": "abc",
                "Last-Modified": "Mon, 01 Jan 2024 00:00:00 GMT",
            },
        )

    monkeypatch.setattr(
        "jobagent.services.company_fetch_service.requests.get",
        fake_get,
    )

    document = fetch_source(
        source,
        repository=repository,
    )
    latest = repository.load_latest_document(
        source.id
    )

    assert document.status_code == 200
    assert document.mime_type == "text/html"
    assert document.charset == "utf-8"
    assert document.content_text == "<html>CareerHub</html>"
    assert document.content_size == len(
        payload
    )
    assert document.content_hash == hashlib.sha256(
        payload
    ).hexdigest()
    assert document.etag == "abc"
    assert latest.id == document.id


def test_fetch_source_http_404_stores_empty_document(tmp_path, monkeypatch):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    source = _source(
        repository
    )

    monkeypatch.setattr(
        "jobagent.services.company_fetch_service.requests.get",
        lambda *args, **kwargs: FakeResponse(
            404,
            b"Not found",
            headers={
                "Content-Type": "text/html",
            },
        ),
    )

    document = fetch_source(
        source,
        repository=repository,
    )

    assert document.status_code == 404
    assert document.content_text == ""
    assert document.content_hash is None
    assert document.content_size == 0


def test_fetch_source_http_500_stores_empty_document(tmp_path, monkeypatch):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    source = _source(
        repository
    )

    monkeypatch.setattr(
        "jobagent.services.company_fetch_service.requests.get",
        lambda *args, **kwargs: FakeResponse(
            500,
            b"Server error",
        ),
    )

    document = fetch_source(
        source,
        repository=repository,
    )

    assert document.status_code == 500
    assert document.content_text == ""
    assert document.content_hash is None


def test_fetch_source_timeout_stores_failure_document(tmp_path, monkeypatch):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    source = _source(
        repository
    )

    def fake_get(*args, **kwargs):
        from jobagent.services.company_fetch_service import requests

        raise requests.Timeout()

    monkeypatch.setattr(
        "jobagent.services.company_fetch_service.requests.get",
        fake_get,
    )

    document = fetch_source(
        source,
        repository=repository,
    )

    assert document.status_code == 0
    assert document.content_text == ""
    assert document.content_hash is None


def test_fetch_company_fetches_enabled_sources_only(tmp_path, monkeypatch):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = repository.upsert_company(
        "Example"
    )
    first = add_company_source(
        company.id,
        SourceType.COMPANY_WEBSITE,
        "https://example.test",
        "Website",
        repository=repository,
    )
    second = add_company_source(
        company.id,
        SourceType.CAREER_PAGE,
        "https://example.test/jobs",
        "Jobs",
        repository=repository,
    )
    repository.disable_company_source(
        second.id
    )

    monkeypatch.setattr(
        "jobagent.services.company_fetch_service.requests.get",
        lambda *args, **kwargs: FakeResponse(
            200,
            b"OK",
            headers={
                "Content-Type": "text/plain; charset=utf-8",
            },
        ),
    )

    documents = fetch_company(
        company.id,
        repository=repository,
    )

    assert len(documents) == 1
    assert documents[0].source_id == first.id


def test_repeated_fetches_create_versions(tmp_path, monkeypatch):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    source = _source(
        repository
    )
    payloads = [
        b"first",
        b"second",
    ]

    def fake_get(*args, **kwargs):
        return FakeResponse(
            200,
            payloads.pop(0),
            headers={
                "Content-Type": "text/plain; charset=utf-8",
            },
        )

    monkeypatch.setattr(
        "jobagent.services.company_fetch_service.requests.get",
        fake_get,
    )

    first = fetch_source(
        source,
        repository=repository,
    )
    second = fetch_source(
        source,
        repository=repository,
    )
    documents = repository.list_documents(
        source.company_id
    )

    assert first.id != second.id
    assert len(documents) == 2
    assert repository.load_latest_document(
        source.id
    ).id == second.id


def test_fetch_company_summary_detects_updated_and_unchanged(tmp_path, monkeypatch):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    source = _source(
        repository
    )
    payloads = [
        b"first",
        b"first",
        b"second",
    ]

    def fake_get(*args, **kwargs):
        return FakeResponse(
            200,
            payloads.pop(0),
            headers={
                "Content-Type": "text/plain; charset=utf-8",
            },
        )

    monkeypatch.setattr(
        "jobagent.services.company_fetch_service.requests.get",
        fake_get,
    )

    first = fetch_company_with_summary(
        source.company_id,
        repository=repository,
    )
    second = fetch_company_with_summary(
        source.company_id,
        repository=repository,
    )
    third = fetch_company_with_summary(
        source.company_id,
        repository=repository,
    )

    assert first.checked == 1
    assert first.successful == 1
    assert first.updated == 1
    assert first.unchanged == 0
    assert second.updated == 0
    assert second.unchanged == 1
    assert third.updated == 1
    assert third.unchanged == 0
    assert "1 Quellen geprüft" in third.message()
