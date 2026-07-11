import logging
import re

from jobagent.models.company_evidence import CompanyEvidence, EvidenceType
from jobagent.models.document_processing_result import DocumentProcessingResult
from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.export_text_service import normalize_export_text


logger = logging.getLogger(__name__)


HEADING_PATTERNS = [
    (EvidenceType.MISSION, ["mission", "unsere mission", "auftrag"]),
    (EvidenceType.VISION, ["vision", "unsere vision", "zukunft"]),
    (EvidenceType.PURPOSE, ["purpose", "warum wir", "wer wir sind", "über uns"]),
    (EvidenceType.BENEFIT, ["benefits", "benefit", "vorteile", "leistungen für mitarbeitende"]),
    (EvidenceType.CULTURE, ["kultur", "unsere werte", "werte", "arbeiten bei"]),
    (EvidenceType.TECHNOLOGY, ["technologien", "technologie", "technology", "tech stack"]),
    (EvidenceType.BUSINESS_UNIT, ["geschäftsbereiche", "business units"]),
    (EvidenceType.PRODUCT, ["produkte", "products"]),
    (EvidenceType.SERVICE, ["leistungen", "services", "dienstleistungen"]),
    (EvidenceType.LOCATION, ["standorte", "locations"]),
    (EvidenceType.INNOVATION, ["innovation", "innovationen", "forschung", "digitalisierung"]),
    (EvidenceType.CAREER, ["karriere", "jobs", "stellenangebote", "arbeiten bei", "jobangebote"]),
    (EvidenceType.TRAVEL, ["reisebereitschaft", "reisetätigkeit", "travel"]),
    (EvidenceType.LANGUAGE, ["sprachen", "languages"]),
    (EvidenceType.SALARY, ["gehalt", "vergütung", "salary"]),
    (EvidenceType.REMOTE, ["remote", "homeoffice"]),
    (EvidenceType.HYBRID, ["hybrid"]),
    (EvidenceType.ONSITE, ["vor ort", "onsite"]),
    (EvidenceType.MANAGEMENT, ["management", "führung", "leadership"]),
    (EvidenceType.SUSTAINABILITY, ["nachhaltigkeit", "sustainability"]),
    (EvidenceType.KRITIS, ["kritis", "kritische infrastruktur", "infrastruktur", "bahn", "energie"]),
]


KEYWORD_PATTERNS = [
    (EvidenceType.MISSION, ["mission", "auftrag"]),
    (EvidenceType.VISION, ["vision"]),
    (EvidenceType.PURPOSE, ["wer wir sind", "über uns", "purpose"]),
    (EvidenceType.CAREER, ["karriere", "jobs", "stellenangebote", "arbeiten bei"]),
    (EvidenceType.BENEFIT, ["benefits", "benefit", "vorteile", "weiterbildung"]),
    (EvidenceType.TECHNOLOGY, ["technologie", "technologien", "digitalisierung", "cloud", "software"]),
    (EvidenceType.INNOVATION, ["innovation", "forschung", "digitalisierung"]),
    (EvidenceType.SUSTAINABILITY, ["nachhaltigkeit", "sustainability"]),
    (EvidenceType.LOCATION, ["standorte", "locations"]),
    (EvidenceType.KRITIS, ["kritis", "kritische infrastruktur", "infrastruktur", "bahn", "energie"]),
]


def _repository(repository: CompanyRepository | None = None) -> CompanyRepository:
    return repository or CompanyRepository()


def _company_id(company) -> int:
    if isinstance(company, dict):
        return int(company.get("id"))

    return int(getattr(company, "id"))


def _normalize_heading(value: str) -> str:
    value = normalize_export_text(value).lower().strip(" :-")
    return re.sub(r"\s+", " ", value)


def _heading_type(line: str) -> EvidenceType | None:
    normalized = _normalize_heading(line)

    if not normalized:
        return None

    for evidence_type, headings in HEADING_PATTERNS:
        for heading in headings:
            if normalized == heading or normalized.startswith(f"{heading}:"):
                return evidence_type

    return None


def _keyword_type(text: str) -> EvidenceType | None:
    normalized = _normalize_heading(text)

    for evidence_type, keywords in KEYWORD_PATTERNS:
        if any(keyword in normalized for keyword in keywords):
            return evidence_type

    return None


def _inferred_title(evidence_type: EvidenceType, fallback: str | None = None) -> str:
    labels = {
        EvidenceType.MISSION: "Mission",
        EvidenceType.VISION: "Vision",
        EvidenceType.PURPOSE: "Über uns",
        EvidenceType.BENEFIT: "Benefits",
        EvidenceType.CULTURE: "Kultur",
        EvidenceType.TECHNOLOGY: "Technologie",
        EvidenceType.BUSINESS_UNIT: "Geschäftsbereiche",
        EvidenceType.LOCATION: "Standorte",
        EvidenceType.INNOVATION: "Innovation",
        EvidenceType.CAREER: "Karriere",
        EvidenceType.SUSTAINABILITY: "Nachhaltigkeit",
        EvidenceType.KRITIS: "Infrastruktur",
        EvidenceType.OTHER: "Dokumentauszug",
    }

    return labels.get(evidence_type) or fallback or "Dokumentauszug"


def _compact_lines(clean_text: str) -> list[str]:
    raw_lines = str(clean_text or "").splitlines()
    lines = []

    for raw_line in raw_lines:
        line = normalize_export_text(raw_line)
        if line:
            lines.append(line)

    if lines:
        return lines

    compact = normalize_export_text(clean_text)
    return [compact] if compact else []


def _sections(clean_text: str) -> list[dict]:
    sections = []
    current = None

    for line in _compact_lines(clean_text):
        evidence_type = _heading_type(line)

        if evidence_type:
            if current and current["lines"]:
                sections.append(current)

            current = {
                "title": line.strip(" :-")[:120],
                "evidence_type": evidence_type,
                "lines": [],
            }
            continue

        if current is None:
            inferred_type = _keyword_type(line) or EvidenceType.OTHER
            current = {
                "title": _inferred_title(inferred_type),
                "evidence_type": inferred_type,
                "lines": [],
            }

        current["lines"].append(line)

    if current and current["lines"]:
        sections.append(current)

    return sections


def _fallback_evidence(
    company_id: int,
    document_processing_result: DocumentProcessingResult,
    metadata: dict,
) -> CompanyEvidence | None:
    clean_text = normalize_export_text(document_processing_result.clean_text)

    if not clean_text:
        return None

    source_name = str(metadata.get("source_name") or document_processing_result.title or "")
    source_url = str(metadata.get("source_url") or metadata.get("url") or "")
    source_type = str(metadata.get("source_type") or document_processing_result.source_type or "")

    return CompanyEvidence(
        company_id=company_id,
        document_id=metadata.get("document_id"),
        evidence_type=EvidenceType.OTHER,
        title=document_processing_result.title or source_name or "Dokumentauszug",
        text=clean_text[:2000],
        source_type=source_type,
        source_name=source_name,
        source_url=source_url,
        section="fallback",
        confidence=0.3,
        language=document_processing_result.language,
    )


def extract_evidence(
    company,
    document_processing_result: DocumentProcessingResult,
) -> list[CompanyEvidence]:
    metadata = document_processing_result.metadata or {}
    company_id = _company_id(company)
    source_type = str(metadata.get("source_type") or document_processing_result.source_type or "")
    source_name = str(metadata.get("source_name") or document_processing_result.title or "")
    source_url = str(metadata.get("source_url") or metadata.get("url") or "")
    document_id = metadata.get("document_id")
    clean_text = normalize_export_text(document_processing_result.clean_text)
    evidence_items = []

    if not clean_text:
        logger.warning(
            "Company evidence extraction skipped empty clean_text company_id=%s document_id=%s steps=%s",
            company_id,
            document_id,
            document_processing_result.processing_steps,
        )
        return []

    for section in _sections(clean_text):
        text = normalize_export_text("\n".join(section["lines"]))

        if not text:
            continue

        evidence_type = section["evidence_type"]
        evidence_items.append(
            CompanyEvidence(
                company_id=company_id,
                document_id=document_id,
                evidence_type=evidence_type,
                title=section["title"] or _inferred_title(evidence_type),
                text=text[:4000],
                source_type=source_type,
                source_name=source_name,
                source_url=source_url,
                section=section["title"],
                confidence=0.75 if evidence_type != EvidenceType.OTHER else 0.4,
                language=document_processing_result.language,
            )
        )

    if not evidence_items:
        fallback = _fallback_evidence(company_id, document_processing_result, metadata)

        if fallback is not None:
            logger.info(
                "Company evidence extraction created fallback evidence company_id=%s document_id=%s",
                company_id,
                document_id,
            )
            evidence_items.append(fallback)

    logger.info(
        "Company evidence extraction summary company_id=%s document_id=%s evidence_count=%s clean_text_size=%s",
        company_id,
        document_id,
        len(evidence_items),
        len(clean_text),
    )

    return evidence_items


def save_company_evidence(
    evidence: CompanyEvidence,
    repository: CompanyRepository | None = None,
) -> CompanyEvidence:
    return _repository(repository).save_company_evidence(evidence)


def list_company_evidence(
    company_id: int,
    repository: CompanyRepository | None = None,
) -> list[CompanyEvidence]:
    return _repository(repository).list_company_evidence(company_id)


def list_company_evidence_by_type(
    company_id: int,
    evidence_type,
    repository: CompanyRepository | None = None,
) -> list[CompanyEvidence]:
    return _repository(repository).list_company_evidence_by_type(
        company_id,
        evidence_type,
    )


def delete_company_evidence(
    evidence_id: int,
    repository: CompanyRepository | None = None,
) -> None:
    _repository(repository).delete_company_evidence(evidence_id)
