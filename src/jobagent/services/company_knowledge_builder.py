from statistics import mean

from jobagent.models.company_concept_candidate import CompanyConceptCandidate
from jobagent.models.company_evidence import EvidenceType
from jobagent.models.company_knowledge_draft import CompanyKnowledgeDraft
from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.company_concept_normalizer import (
    canonicalize_company_concepts,
    extract_company_concepts,
)
from jobagent.services.export_text_service import normalize_export_text
from jobagent.services.skill_candidate_domain_service import normalize_domain_text


def _repository(repository: CompanyRepository | None = None) -> CompanyRepository:
    return repository or CompanyRepository()


def _value(value) -> str:
    return str(value.value if hasattr(value, "value") else value)


def _texts(evidence_items, evidence_type) -> list[str]:
    expected = _value(evidence_type)

    return [
        normalized
        for normalized in (
            normalize_export_text(evidence.text)
            for evidence in evidence_items
            if _value(evidence.evidence_type) == expected
        )
        if normalized
    ]


def _first_text(evidence_items, evidence_type) -> str | None:
    values = _texts(evidence_items, evidence_type)
    return values[0] if values else None


def _dedupe(values) -> list[str]:
    seen = set()
    result = []

    for value in values or []:
        normalized = normalize_export_text(str(value or ""))
        key = normalize_domain_text(normalized)

        if not normalized or key in seen:
            continue

        seen.add(key)
        result.append(normalized)

    return result


def _source_document_ids(evidence_items) -> list[int]:
    return sorted(
        {
            int(evidence.document_id)
            for evidence in evidence_items
            if evidence.document_id is not None
        }
    )


def _source_evidence_ids(evidence_items) -> list[int]:
    return sorted(
        {
            int(evidence.id)
            for evidence in evidence_items
            if evidence.id is not None
        }
    )


def _concepts_from_evidence(evidence_items) -> list[CompanyConceptCandidate]:
    return [
        concept
        for evidence in evidence_items
        for concept in extract_company_concepts(evidence)
    ]


def _concept_values(concepts: list[CompanyConceptCandidate], concept_type: str) -> list[str]:
    return _dedupe(
        [
            concept.canonical_value
            for concept in concepts
            if concept.concept_type == concept_type
        ]
    )


def _concept_values_for_evidence_types(
    concepts: list[CompanyConceptCandidate],
    concept_type: str,
    evidence_items,
    evidence_types,
) -> list[str]:
    allowed_types = {
        _value(evidence_type)
        for evidence_type in evidence_types
    }
    allowed_evidence_ids = {
        evidence.id
        for evidence in evidence_items
        if evidence.id is not None
        and _value(evidence.evidence_type) in allowed_types
    }

    return _dedupe(
        [
            concept.canonical_value
            for concept in concepts
            if concept.concept_type == concept_type
            and concept.source_evidence_id in allowed_evidence_ids
        ]
    )


def _canonical_concept_labels(concepts: list[CompanyConceptCandidate]) -> list[str]:
    return _dedupe(
        [
            f"{concept.concept_type}:{concept.canonical_value}"
            for concept in concepts
            if concept.canonical_value
        ]
    )


def _concept_statistics(
    raw_concepts: list[CompanyConceptCandidate],
    canonical_concepts: list[CompanyConceptCandidate],
) -> dict[str, float | int]:
    raw_keys = {
        (
            concept.concept_type,
            normalize_domain_text(concept.raw_value),
        )
        for concept in raw_concepts
    }
    canonical_keys = {
        (
            concept.concept_type,
            normalize_domain_text(concept.canonical_value),
        )
        for concept in canonical_concepts
    }
    unknown = [
        concept
        for concept in canonical_concepts
        if concept.concept_type == "other"
    ]
    confidences = [
        concept.confidence
        for concept in canonical_concepts
        if concept.confidence is not None
    ]

    return {
        "total": len(raw_concepts),
        "canonical": len(canonical_concepts),
        "merged": max(0, len(raw_keys) - len(canonical_keys)),
        "unknown": len(unknown),
        "confidence_avg": round(mean(confidences), 4) if confidences else 0.0,
    }


def _confidence(evidence_items, canonical_concepts) -> float:
    if not evidence_items and not canonical_concepts:
        return 0.0

    if canonical_concepts:
        values = [
            concept.confidence
            for concept in canonical_concepts
            if concept.confidence is not None
        ]
        return round(min(0.95, mean(values) if values else 0.5), 2)

    typed_evidence = [
        evidence
        for evidence in evidence_items
        if _value(evidence.evidence_type) != EvidenceType.OTHER.value
    ]
    ratio = len(typed_evidence) / len(evidence_items)

    return round(min(0.95, 0.25 + ratio * 0.7), 2)


def build_company_knowledge(
    company_id: int,
    repository: CompanyRepository | None = None,
) -> CompanyKnowledgeDraft:
    repo = _repository(repository)
    evidence_items = repo.list_company_evidence(company_id)
    raw_concepts = _concepts_from_evidence(evidence_items)
    canonical_concepts = canonicalize_company_concepts(raw_concepts)
    concept_statistics = _concept_statistics(raw_concepts, canonical_concepts)

    draft = CompanyKnowledgeDraft(
        company_id=company_id,
        mission=_first_text(evidence_items, EvidenceType.MISSION),
        vision=_first_text(evidence_items, EvidenceType.VISION),
        culture=_first_text(evidence_items, EvidenceType.CULTURE),
        business_domains=_concept_values(canonical_concepts, "company_domain"),
        mission_keywords=_concept_values_for_evidence_types(
            canonical_concepts,
            "mission_term",
            evidence_items,
            [
                EvidenceType.MISSION,
                EvidenceType.VISION,
                EvidenceType.PURPOSE,
            ],
        ),
        industries=_concept_values(canonical_concepts, "industry"),
        technologies=_concept_values(canonical_concepts, "technology"),
        work_models=_concept_values(canonical_concepts, "work_model"),
        locations=_concept_values(canonical_concepts, "location"),
        innovation_areas=_concept_values(canonical_concepts, "innovation"),
        benefits=_concept_values(canonical_concepts, "benefit"),
        kritis_relevance=bool(_concept_values(canonical_concepts, "kritis")),
        confidence=_confidence(evidence_items, canonical_concepts),
        evidence_count=len(evidence_items),
        source_documents=_source_document_ids(evidence_items),
        source_evidence_ids=_source_evidence_ids(evidence_items),
        canonical_concepts=_canonical_concept_labels(canonical_concepts),
        concept_statistics=concept_statistics,
        review_method="rule_based",
    )

    return repo.save_company_knowledge_draft(draft)


def load_latest_company_knowledge_draft(
    company_id: int,
    repository: CompanyRepository | None = None,
) -> CompanyKnowledgeDraft | None:
    return _repository(repository).load_latest_company_knowledge_draft(company_id)


def list_company_knowledge_drafts(
    company_id: int,
    repository: CompanyRepository | None = None,
) -> list[CompanyKnowledgeDraft]:
    return _repository(repository).list_company_knowledge_drafts(company_id)
