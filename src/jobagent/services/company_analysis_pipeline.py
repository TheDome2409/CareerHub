import hashlib
import logging
import re
import time

from jobagent.models.company_analysis_summary import CompanyAnalysisSummary
from jobagent.models.company_document import CompanyDocument
from jobagent.models.company_evidence import CompanyEvidence
from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.company_evidence_service import extract_evidence
from jobagent.services.document_processing_service import process_document


logger = logging.getLogger(__name__)


def _repository(repository: CompanyRepository | None = None) -> CompanyRepository:
    return repository or CompanyRepository()


def _text_hash(text: str | None) -> str:
    normalized = re.sub(
        r"\s+",
        " ",
        str(text or "").strip(),
    )

    return hashlib.sha256(
        normalized.encode(
            "utf-8"
        )
    ).hexdigest()


def _value(value) -> str:
    return str(
        value.value if hasattr(value, "value") else value
    )


def _same_slot(
    left: CompanyEvidence,
    right: CompanyEvidence,
) -> bool:
    return (
        _value(left.evidence_type) == _value(right.evidence_type)
        and (left.source_url or "") == (right.source_url or "")
        and (left.source_name or "") == (right.source_name or "")
        and (left.section or "") == (right.section or "")
    )


def _merge_summary(
    target: CompanyAnalysisSummary,
    partial: CompanyAnalysisSummary,
) -> None:
    target.documents_processed += partial.documents_processed
    target.documents_skipped += partial.documents_skipped
    target.evidence_created += partial.evidence_created
    target.evidence_updated += partial.evidence_updated
    target.evidence_unchanged += partial.evidence_unchanged
    target.errors.extend(
        partial.errors
    )


def _document_metadata(
    document: CompanyDocument,
    repository: CompanyRepository,
) -> dict:
    source = repository.get_company_source(
        document.source_id
    )

    return {
        "document_id": document.id,
        "source_id": document.source_id,
        "source_type": (
            str(source.source_type) if source else document.content_type or ""
        ),
        "source_name": (
            source.title if source else document.title or document.url
        ),
        "source_url": (
            source.url if source else document.url
        ),
        "url": document.url,
    }


def analyze_company_document(
    document: CompanyDocument,
    repository: CompanyRepository | None = None,
) -> CompanyAnalysisSummary:
    repo = _repository(
        repository
    )
    started_at = time.monotonic()
    summary = CompanyAnalysisSummary(
        company_id=document.company_id
    )

    try:
        if not str(document.content_text or "").strip():
            logger.info(
                "Skipping empty company document id=%s company_id=%s",
                document.id,
                document.company_id,
            )
            summary.documents_skipped = 1
            return summary

        logger.info(
            "Document Processing document_id=%s company_id=%s",
            document.id,
            document.company_id,
        )
        metadata = _document_metadata(
            document,
            repo,
        )
        processing_result = process_document(
            document.content_text,
            mime_type=document.mime_type or document.content_type,
            encoding=document.charset,
            title=document.title,
            metadata=metadata,
        )
        summary.documents_processed = 1

        if not str(processing_result.clean_text or "").strip():
            logger.warning(
                "Company document processing produced empty clean_text document_id=%s company_id=%s steps=%s",
                document.id,
                document.company_id,
                processing_result.processing_steps,
            )

        logger.info(
            "Evidence Extraction document_id=%s company_id=%s",
            document.id,
            document.company_id,
        )
        evidence_items = extract_evidence(
            {
                "id": document.company_id,
            },
            processing_result,
        )
        if not evidence_items:
            logger.warning(
                "Evidence Extraction produced 0 evidence document_id=%s company_id=%s clean_text_size=%s",
                document.id,
                document.company_id,
                len(processing_result.clean_text or ""),
            )
        existing_evidence = repo.list_company_evidence(
            document.company_id
        )

        for evidence in evidence_items:
            text_hash = _text_hash(
                evidence.text
            )
            existing = repo.find_existing_evidence(
                company_id=evidence.company_id,
                evidence_type=evidence.evidence_type,
                text_hash=text_hash,
            )

            if existing is not None:
                summary.evidence_unchanged += 1
                continue

            matching_slot_exists = any(
                _same_slot(
                    current,
                    evidence,
                )
                for current in existing_evidence
            )
            saved, created = repo.upsert_company_evidence(
                evidence
            )
            existing_evidence.append(
                saved
            )

            if matching_slot_exists and created:
                summary.evidence_updated += 1
            elif created:
                summary.evidence_created += 1
            else:
                summary.evidence_unchanged += 1

            logger.info(
                "Repository Save evidence_id=%s company_id=%s type=%s created=%s",
                saved.id,
                saved.company_id,
                saved.evidence_type,
                created,
            )
    except Exception as exc:
        logger.info(
            "Company document analysis failed document_id=%s: %s",
            document.id,
            exc,
        )
        summary.errors.append(
            str(exc)
        )
    finally:
        summary.processing_time_ms = int(
            (time.monotonic() - started_at) * 1000
        )
        logger.info(
            "Summary %s",
            summary.message(),
        )

    return summary


def analyze_all_documents(
    company_id: int,
    repository: CompanyRepository | None = None,
) -> CompanyAnalysisSummary:
    repo = _repository(
        repository
    )
    started_at = time.monotonic()
    summary = CompanyAnalysisSummary(
        company_id=company_id
    )

    for document in repo.list_documents(
        company_id
    ):
        partial = analyze_company_document(
            document,
            repository=repo,
        )
        _merge_summary(
            summary,
            partial,
        )

    summary.processing_time_ms = int(
        (time.monotonic() - started_at) * 1000
    )
    logger.info(
        "Summary %s",
        summary.message(),
    )

    return summary


def analyze_company(
    company_id: int,
    repository: CompanyRepository | None = None,
) -> CompanyAnalysisSummary:
    return analyze_all_documents(
        company_id,
        repository=repository,
    )
