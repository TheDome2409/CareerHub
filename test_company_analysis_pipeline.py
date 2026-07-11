from jobagent.models.company_document import CompanyDocument
from jobagent.models.company_evidence import CompanyEvidence, EvidenceType
from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.company_analysis_pipeline import (
    analyze_all_documents,
    analyze_company,
    analyze_company_document,
)
from jobagent.services.company_source_service import add_company_source


def _company_and_source(repository: CompanyRepository):
    company = repository.upsert_company(
        "Dataport"
    )
    source = add_company_source(
        company.id,
        "company_website",
        "https://example.test",
        "Website",
        repository=repository,
    )

    return company, source


def _document(
    repository: CompanyRepository,
    company_id: int,
    source_id: int,
    text: str,
    fetched_at: str = "2026-01-01T00:00:00+00:00",
    mime_type: str = "text/plain",
):
    return repository.save_company_document(
        CompanyDocument(
            company_id=company_id,
            source_id=source_id,
            url="https://example.test",
            title="Website",
            content_type=mime_type,
            mime_type=mime_type,
            charset="utf-8",
            content_text=text,
            status_code=200,
            content_size=len(
                text.encode("utf-8")
            ),
            fetched_at=fetched_at,
        )
    )


def test_analyze_company_document_creates_evidence(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company, source = _company_and_source(
        repository
    )
    document = _document(
        repository,
        company.id,
        source.id,
        "Mission\nWir digitalisieren öffentliche Verwaltung.",
    )

    summary = analyze_company_document(
        document,
        repository=repository,
    )
    evidence = repository.list_company_evidence(
        company.id
    )

    assert summary.documents_processed == 1
    assert summary.evidence_created == 1
    assert summary.evidence_unchanged == 0
    assert summary.errors == []
    assert len(evidence) == 1
    assert evidence[0].document_id == document.id
    assert evidence[0].evidence_type == "mission"


def test_analyze_all_documents_processes_multiple_documents(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company, source = _company_and_source(
        repository
    )
    _document(
        repository,
        company.id,
        source.id,
        "Mission\nWir bauen digitale Infrastruktur.",
        fetched_at="2026-01-01T00:00:00+00:00",
    )
    _document(
        repository,
        company.id,
        source.id,
        "Benefits\nFlexible Arbeitsmodelle.",
        fetched_at="2026-01-02T00:00:00+00:00",
    )

    summary = analyze_all_documents(
        company.id,
        repository=repository,
    )

    assert summary.documents_processed == 2
    assert summary.evidence_created == 2
    assert len(
        repository.list_company_evidence(
            company.id
        )
    ) == 2


def test_analyze_html_documents_creates_keyword_or_fallback_evidence(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company, source = _company_and_source(
        repository
    )
    _document(
        repository,
        company.id,
        source.id,
        """
        <html><body>
        <main>DB InfraGO betreibt die Eisenbahninfrastruktur.</main>
        </body></html>
        """,
        fetched_at="2026-01-01T00:00:00+00:00",
        mime_type="text/html",
    )
    _document(
        repository,
        company.id,
        source.id,
        """
        <html><body>
        <h2>Karriere</h2>
        <p>Jobs mit Verantwortung und Weiterbildung.</p>
        </body></html>
        """,
        fetched_at="2026-01-02T00:00:00+00:00",
        mime_type="text/html",
    )

    summary = analyze_company(
        company.id,
        repository=repository,
    )
    evidence = repository.list_company_evidence(
        company.id
    )

    assert summary.documents_processed == 2
    assert summary.evidence_created >= 2
    assert len(evidence) >= 2
    assert {
        item.evidence_type
        for item in evidence
    } & {
        "career",
        "kritis",
        "other",
    }


def test_empty_document_is_skipped(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company, source = _company_and_source(
        repository
    )
    document = _document(
        repository,
        company.id,
        source.id,
        "",
    )

    summary = analyze_company_document(
        document,
        repository=repository,
    )

    assert summary.documents_processed == 0
    assert summary.documents_skipped == 1
    assert repository.list_company_evidence(
        company.id
    ) == []


def test_repeated_analysis_keeps_identical_evidence_unchanged(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company, source = _company_and_source(
        repository
    )
    _document(
        repository,
        company.id,
        source.id,
        "Vision\nEine moderne digitale Infrastruktur.",
    )

    first = analyze_company(
        company.id,
        repository=repository,
    )
    second = analyze_company(
        company.id,
        repository=repository,
    )

    assert first.evidence_created == 1
    assert second.evidence_created == 0
    assert second.evidence_unchanged == 1
    assert len(
        repository.list_company_evidence(
            company.id
        )
    ) == 1


def test_changed_evidence_in_same_slot_is_counted_as_updated(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company, source = _company_and_source(
        repository
    )
    _document(
        repository,
        company.id,
        source.id,
        "Mission\nAlte Mission.",
        fetched_at="2026-01-01T00:00:00+00:00",
    )
    _document(
        repository,
        company.id,
        source.id,
        "Mission\nNeue Mission.",
        fetched_at="2026-01-02T00:00:00+00:00",
    )

    summary = analyze_all_documents(
        company.id,
        repository=repository,
    )

    assert summary.evidence_created == 1
    assert summary.evidence_updated == 1
    assert len(
        repository.list_company_evidence_by_type(
            company.id,
            EvidenceType.MISSION,
        )
    ) == 2


def test_repository_find_and_upsert_company_evidence(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company, _source = _company_and_source(
        repository
    )
    evidence = CompanyEvidence(
        company_id=company.id,
        evidence_type=EvidenceType.CAREER,
        title="Karriere",
        text="Wir suchen Menschen für digitale Verwaltung.",
        source_type="career_page",
        source_name="Karriere",
        source_url="https://example.test/jobs",
        section="Karriere",
        confidence=0.75,
    )

    first, first_created = repository.upsert_company_evidence(
        evidence
    )
    second, second_created = repository.upsert_company_evidence(
        evidence
    )

    assert first_created is True
    assert second_created is False
    assert first.id == second.id
    assert len(
        repository.list_company_evidence(
            company.id
        )
    ) == 1
