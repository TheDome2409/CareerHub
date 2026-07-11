import logging
import time

from jobagent.models.company_pipeline_report import CompanyPipelineReport
from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.company_concept_normalizer import (
    canonicalize_company_concepts,
    extract_company_concepts,
)
from jobagent.services.document_processing_service import process_document


logger = logging.getLogger(__name__)


def _repository(repository: CompanyRepository | None = None) -> CompanyRepository:
    return repository or CompanyRepository()


def _source_dict(source) -> dict:
    return {
        "id": source.id,
        "title": source.title,
        "source_type": str(source.source_type),
        "url": source.url,
        "enabled": source.enabled,
        "priority": source.priority,
        "last_checked": source.last_checked,
        "last_success": source.last_success,
        "content_hash": source.content_hash,
    }


def _document_dict(document) -> dict:
    return {
        "id": document.id,
        "source_id": document.source_id,
        "title": document.title,
        "url": document.url,
        "status_code": document.status_code,
        "content_type": document.content_type,
        "mime_type": document.mime_type,
        "content_size": document.content_size,
        "content_hash": document.content_hash,
        "fetched_at": document.fetched_at,
    }


def _document_metadata(document, repository: CompanyRepository) -> dict:
    source = repository.get_company_source(document.source_id)

    return {
        "document_id": document.id,
        "source_id": document.source_id,
        "source_type": str(source.source_type) if source else document.content_type or "",
        "source_name": source.title if source else document.title or document.url,
        "source_url": source.url if source else document.url,
        "url": document.url,
    }


def inspect_company(
    company_id: int,
    repository: CompanyRepository | None = None,
) -> CompanyPipelineReport:
    repo = _repository(repository)
    started = time.perf_counter()
    report = CompanyPipelineReport(company_id=company_id)

    try:
        sources = repo.list_company_sources(company_id=company_id, include_disabled=True)
        report.sources = [_source_dict(source) for source in sources]

        if not sources:
            report.warnings.append("Keine Quellen hinterlegt.")

        documents = repo.list_documents(company_id)
        report.documents = [_document_dict(document) for document in documents]
        report.document_sizes = {
            int(document.id): document.content_size
            for document in documents
            if document.id is not None
        }

        if not documents:
            report.warnings.append("Keine Dokumente gespeichert.")

        for document in documents:
            document_started = time.perf_counter()

            try:
                processing_result = process_document(
                    document.content_text,
                    mime_type=document.mime_type or document.content_type,
                    encoding=document.charset,
                    title=document.title,
                    metadata=_document_metadata(document, repo),
                )
                document_id = int(document.id)
                report.processing_results[document_id] = processing_result
                report.clean_text_lengths[document_id] = len(
                    processing_result.clean_text or ""
                )

                if not str(processing_result.clean_text or "").strip():
                    report.warnings.append(
                        f"Dokument {document_id}: Clean Text leer."
                    )

                logger.info(
                    "Company pipeline inspector processing company_id=%s document_id=%s duration_ms=%s clean_text_length=%s",
                    company_id,
                    document_id,
                    int((time.perf_counter() - document_started) * 1000),
                    report.clean_text_lengths[document_id],
                )
            except Exception as exc:
                report.errors.append(
                    f"Dokument {document.id}: {exc}"
                )
                logger.info(
                    "Company pipeline inspector processing failed company_id=%s document_id=%s error=%s",
                    company_id,
                    document.id,
                    exc,
                )

        evidence_items = repo.list_company_evidence(company_id)
        report.evidence_count = len(evidence_items)

        for evidence in evidence_items:
            evidence_type = str(evidence.evidence_type)
            report.evidence_by_type[evidence_type] = (
                report.evidence_by_type.get(evidence_type, 0) + 1
            )

        if documents and not evidence_items:
            report.warnings.append("Dokumente vorhanden, aber keine Evidence gespeichert.")

        concept_candidates = [
            concept
            for evidence in evidence_items
            for concept in extract_company_concepts(evidence)
        ]
        canonical_concepts = canonicalize_company_concepts(concept_candidates)
        report.concept_candidates = [
            concept.model_dump(mode="json")
            for concept in concept_candidates
        ]
        report.canonical_concepts = [
            f"{concept.concept_type}:{concept.canonical_value}"
            for concept in canonical_concepts
        ]
        report.unknown_concepts = [
            concept.raw_value
            for concept in canonical_concepts
            if concept.concept_type == "other"
        ]

        for concept in canonical_concepts:
            report.concept_types[concept.concept_type] = (
                report.concept_types.get(concept.concept_type, 0) + 1
            )

        draft = repo.load_latest_company_knowledge_draft(company_id)
        report.knowledge_draft_exists = draft is not None

        if draft is None:
            report.warnings.append("Kein Knowledge Draft vorhanden.")
        else:
            report.knowledge_confidence = draft.confidence
            report.review_method = draft.review_method
            report.review_model = draft.review_model

        logger.info(
            "Company pipeline inspector summary company_id=%s sources=%s documents=%s evidence=%s knowledge=%s duration_ms=%s",
            company_id,
            len(report.sources),
            len(report.documents),
            report.evidence_count,
            report.knowledge_draft_exists,
            int((time.perf_counter() - started) * 1000),
        )
    except Exception as exc:
        report.errors.append(str(exc))
        logger.info(
            "Company pipeline inspector failed company_id=%s error=%s",
            company_id,
            exc,
        )

    return report
