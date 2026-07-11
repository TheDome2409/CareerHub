from pathlib import Path

import yaml

from jobagent.models.company_concept_candidate import CompanyConceptCandidate
from jobagent.models.company_evidence import EvidenceType
from jobagent.services.skill_candidate_domain_service import normalize_domain_text


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_COMPANY_TAXONOMY_DIR = PROJECT_ROOT / "config" / "company_taxonomy"

CONCEPT_TYPES = {
    "company_domain",
    "technology",
    "benefit",
    "work_model",
    "mission_term",
    "industry",
    "kritis",
    "infrastructure",
    "service",
    "relationship",
    "location",
    "other",
}

TAXONOMY_FILES = {
    "benefit": "benefits.yaml",
    "work_model": "work_models.yaml",
    "technology": "technologies.yaml",
    "company_domain": "business_domains.yaml",
    "mission_term": "mission_terms.yaml",
    "kritis": "kritis.yaml",
    "other": "aliases.yaml",
}

EVIDENCE_TYPE_CONCEPT_TYPE = {
    EvidenceType.BENEFIT.value: "benefit",
    EvidenceType.REMOTE.value: "work_model",
    EvidenceType.HYBRID.value: "work_model",
    EvidenceType.ONSITE.value: "work_model",
    EvidenceType.TECHNOLOGY.value: "technology",
    EvidenceType.BUSINESS_UNIT.value: "company_domain",
    EvidenceType.MISSION.value: "mission_term",
    EvidenceType.VISION.value: "mission_term",
    EvidenceType.PURPOSE.value: "mission_term",
    EvidenceType.KRITIS.value: "kritis",
    EvidenceType.SERVICE.value: "service",
    EvidenceType.LOCATION.value: "location",
}


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}

    try:
        data = yaml.safe_load(
            path.read_text(encoding="utf-8")
        )
    except (OSError, yaml.YAMLError):
        return {}

    return data if isinstance(data, dict) else {}


def _concept_entries(taxonomy_dir: Path = DEFAULT_COMPANY_TAXONOMY_DIR) -> list[dict]:
    entries = []

    for concept_type, filename in TAXONOMY_FILES.items():
        data = _load_yaml(taxonomy_dir / filename)
        concepts = data.get("concepts", data)

        if not isinstance(concepts, dict):
            continue

        for canonical_value, config in concepts.items():
            aliases = []
            effective_type = concept_type

            if isinstance(config, dict):
                aliases = list(config.get("aliases", []) or [])
                effective_type = str(
                    config.get("concept_type") or concept_type
                )
            elif isinstance(config, list):
                aliases = list(config)

            aliases.append(canonical_value)

            for alias in aliases:
                raw = str(alias or "").strip()

                if not raw:
                    continue

                entries.append(
                    {
                        "concept_type": effective_type,
                        "canonical_value": str(canonical_value),
                        "raw_value": raw,
                        "normalized": normalize_domain_text(raw),
                    }
                )

    return entries


def _evidence_type(evidence) -> str:
    value = getattr(evidence, "evidence_type", "")
    return str(value.value if hasattr(value, "value") else value)


def _source_type(evidence) -> str:
    return str(getattr(evidence, "source_type", "") or "")


def _base_confidence(evidence, matched_alias: bool) -> float:
    try:
        evidence_confidence = float(getattr(evidence, "confidence", 0.5) or 0.5)
    except (TypeError, ValueError):
        evidence_confidence = 0.5

    if matched_alias:
        return min(0.95, max(0.55, round(evidence_confidence + 0.1, 2)))

    return min(0.75, max(0.35, round(evidence_confidence, 2)))


def _candidate_from_match(evidence, entry: dict) -> CompanyConceptCandidate:
    return CompanyConceptCandidate(
        raw_value=entry["raw_value"],
        canonical_value=entry["canonical_value"],
        concept_type=entry["concept_type"],
        confidence=_base_confidence(evidence, matched_alias=True),
        source_evidence_id=getattr(evidence, "id", None),
        source_document_id=getattr(evidence, "document_id", None),
        source_type=_source_type(evidence),
        reason=f"Alias '{entry['raw_value']}' in Evidence erkannt.",
    )


def _candidate_from_evidence_type(evidence) -> CompanyConceptCandidate | None:
    concept_type = EVIDENCE_TYPE_CONCEPT_TYPE.get(_evidence_type(evidence), "other")
    raw_value = str(getattr(evidence, "title", "") or "").strip()

    if not raw_value:
        return None

    if normalize_domain_text(raw_value) in {
        normalize_domain_text(value)
        for value in EVIDENCE_TYPE_CONCEPT_TYPE
    }:
        return None

    return CompanyConceptCandidate(
        raw_value=raw_value,
        canonical_value=raw_value,
        concept_type=concept_type,
        confidence=_base_confidence(evidence, matched_alias=False),
        source_evidence_id=getattr(evidence, "id", None),
        source_document_id=getattr(evidence, "document_id", None),
        source_type=_source_type(evidence),
        reason="Aus Evidence-Typ abgeleitet.",
    )


def normalize_company_concept(
    candidate: CompanyConceptCandidate,
    taxonomy_dir: str | Path | None = None,
) -> CompanyConceptCandidate:
    taxonomy_path = Path(taxonomy_dir or DEFAULT_COMPANY_TAXONOMY_DIR)
    normalized_raw = normalize_domain_text(candidate.raw_value)
    entries = _concept_entries(taxonomy_path)

    for entry in entries:
        if (
            candidate.concept_type
            and candidate.concept_type == entry["concept_type"]
            and normalized_raw == entry["normalized"]
        ):
            return candidate.model_copy(
                update={
                    "canonical_value": entry["canonical_value"],
                    "concept_type": entry["concept_type"],
                    "confidence": min(0.95, max(candidate.confidence, 0.7)),
                    "reason": candidate.reason or "Company-Taxonomy Alias erkannt.",
                }
            )

    for entry in entries:
        if normalized_raw == entry["normalized"]:
            return candidate.model_copy(
                update={
                    "canonical_value": entry["canonical_value"],
                    "concept_type": entry["concept_type"],
                    "confidence": min(0.95, max(candidate.confidence, 0.7)),
                    "reason": candidate.reason or "Company-Taxonomy Alias erkannt.",
                }
            )

    concept_type = (
        candidate.concept_type
        if candidate.concept_type in CONCEPT_TYPES
        else "other"
    )

    return candidate.model_copy(
        update={
            "concept_type": concept_type,
        }
    )


def extract_company_concepts(
    evidence,
    taxonomy_dir: str | Path | None = None,
) -> list[CompanyConceptCandidate]:
    taxonomy_path = Path(taxonomy_dir or DEFAULT_COMPANY_TAXONOMY_DIR)
    text = " ".join(
        str(value or "")
        for value in [
            getattr(evidence, "title", ""),
            getattr(evidence, "text", ""),
        ]
    )
    normalized_text = normalize_domain_text(text)
    candidates = []

    for entry in _concept_entries(taxonomy_path):
        if entry["normalized"] and entry["normalized"] in normalized_text:
            candidates.append(
                _candidate_from_match(evidence, entry)
            )

    inferred = _candidate_from_evidence_type(evidence)

    if inferred is not None:
        candidates.append(
            normalize_company_concept(
                inferred,
                taxonomy_path,
            )
        )

    return canonicalize_company_concepts(
        candidates,
        taxonomy_path,
    )


def canonicalize_company_concepts(
    candidates,
    taxonomy_dir: str | Path | None = None,
) -> list[CompanyConceptCandidate]:
    taxonomy_path = Path(taxonomy_dir or DEFAULT_COMPANY_TAXONOMY_DIR)
    merged: dict[tuple[str, str], CompanyConceptCandidate] = {}

    for candidate in candidates or []:
        normalized = normalize_company_concept(
            candidate,
            taxonomy_path,
        )
        key = (
            normalized.concept_type,
            normalize_domain_text(normalized.canonical_value),
        )
        previous = merged.get(key)

        if previous is None or normalized.confidence > previous.confidence:
            merged[key] = normalized

    return sorted(
        merged.values(),
        key=lambda item: (
            item.concept_type,
            item.canonical_value.lower(),
        ),
    )
