from jobagent.models.company_document import CompanyDocument
from jobagent.models.company_evidence import CompanyEvidence, EvidenceType
from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.company_knowledge_builder import build_company_knowledge
from jobagent.services.company_pipeline_inspector import inspect_company
from jobagent.services.company_source_service import add_company_source


def _company_source_document(repository: CompanyRepository, text: str):
    company = repository.upsert_company("DB InfraGO")
    source = add_company_source(
        company.id,
        "company_website",
        "https://example.test",
        "Website",
        repository=repository,
    )
    document = repository.save_company_document(
        CompanyDocument(
            company_id=company.id,
            source_id=source.id,
            url=source.url,
            title="Website",
            content_type="text/html",
            mime_type="text/html",
            charset="utf-8",
            content_text=text,
            status_code=200,
            content_size=len(text.encode("utf-8")),
            fetched_at="2026-01-01T00:00:00+00:00",
        )
    )

    return company, source, document


def test_inspect_company_reports_pipeline_state(tmp_path):
    repository = CompanyRepository(tmp_path / "companyhub.db")
    company, _source, document = _company_source_document(
        repository,
        "<html><body><h1>Karriere</h1><p>Jobs mit Verantwortung.</p></body></html>",
    )
    repository.save_company_evidence(
        CompanyEvidence(
            company_id=company.id,
            document_id=document.id,
            evidence_type=EvidenceType.CAREER,
            title="Karriere",
            text="Jobs mit Verantwortung und Weiterbildung.",
            source_type="career_page",
            source_name="Website",
            source_url="https://example.test",
            confidence=0.75,
        )
    )
    draft = build_company_knowledge(
        company.id,
        repository=repository,
    )

    report = inspect_company(
        company.id,
        repository=repository,
    )

    assert report.company_id == company.id
    assert len(report.sources) == 1
    assert len(report.documents) == 1
    assert report.document_sizes[document.id] == document.content_size
    assert report.clean_text_lengths[document.id] > 0
    assert document.id in report.processing_results
    assert report.evidence_count == 1
    assert report.evidence_by_type == {
        "career": 1,
    }
    assert report.knowledge_draft_exists is True
    assert report.knowledge_confidence == draft.confidence
    assert report.review_method == "rule_based"
    assert report.concept_candidates
    assert "benefit:Professional Development" in report.canonical_concepts
    assert report.concept_types["benefit"] == 1


def test_inspect_company_warns_about_missing_pipeline_parts(tmp_path):
    repository = CompanyRepository(tmp_path / "companyhub.db")
    company = repository.upsert_company("Empty")

    report = inspect_company(
        company.id,
        repository=repository,
    )

    assert "Keine Quellen hinterlegt." in report.warnings
    assert "Keine Dokumente gespeichert." in report.warnings
    assert "Kein Knowledge Draft vorhanden." in report.warnings
    assert report.errors == []


def test_inspect_company_warns_when_document_has_empty_clean_text(tmp_path):
    repository = CompanyRepository(tmp_path / "companyhub.db")
    company, _source, document = _company_source_document(
        repository,
        "",
    )

    report = inspect_company(
        company.id,
        repository=repository,
    )

    assert report.clean_text_lengths[document.id] == 0
    assert any("Clean Text leer" in warning for warning in report.warnings)
    assert any("keine evidence" in warning.lower() for warning in report.warnings)
