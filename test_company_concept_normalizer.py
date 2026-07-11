from jobagent.models.company_concept_candidate import CompanyConceptCandidate
from jobagent.models.company_evidence import CompanyEvidence, EvidenceType
from jobagent.services.company_concept_normalizer import (
    canonicalize_company_concepts,
    extract_company_concepts,
    normalize_company_concept,
)


def _evidence(evidence_type, text: str, title: str = "Evidence"):
    return CompanyEvidence(
        id=7,
        company_id=1,
        document_id=3,
        evidence_type=evidence_type,
        title=title,
        text=text,
        source_type="company_website",
        source_name="Website",
        source_url="https://example.test",
        confidence=0.7,
    )


def test_extract_work_model_alias_to_hybrid():
    concepts = extract_company_concepts(
        _evidence(
            EvidenceType.BENEFIT,
            "Wir bieten mobiles Arbeiten und flexible Arbeitszeiten.",
        )
    )

    values = {
        concept.canonical_value
        for concept in concepts
    }

    assert "Hybrid" in values
    assert "Flexible Working Hours" in values


def test_extract_business_domain_and_infrastructure_aliases():
    concepts = extract_company_concepts(
        _evidence(
            EvidenceType.KRITIS,
            "Digital Farming trifft auf Übertragungsnetz und Energienetz.",
        )
    )
    pairs = {
        (
            concept.concept_type,
            concept.canonical_value,
        )
        for concept in concepts
    }

    assert (
        "company_domain",
        "Agricultural Digitalization",
    ) in pairs
    assert (
        "company_domain",
        "Transmission Grid",
    ) in pairs


def test_normalize_company_concept_uses_alias_mapping():
    candidate = CompanyConceptCandidate(
        raw_value="Microsoft Azure",
        canonical_value="Microsoft Azure",
        concept_type="technology",
        confidence=0.4,
    )

    normalized = normalize_company_concept(
        candidate
    )

    assert normalized.canonical_value == "Azure"
    assert normalized.concept_type == "technology"
    assert normalized.confidence >= 0.7


def test_canonicalize_company_concepts_deduplicates_by_type_and_canonical_value():
    concepts = canonicalize_company_concepts(
        [
            CompanyConceptCandidate(
                raw_value="Azure Cloud",
                canonical_value="Azure Cloud",
                concept_type="technology",
                confidence=0.6,
            ),
            CompanyConceptCandidate(
                raw_value="Microsoft Azure",
                canonical_value="Microsoft Azure",
                concept_type="technology",
                confidence=0.8,
            ),
        ]
    )

    assert len(concepts) == 1
    assert concepts[0].canonical_value == "Azure"
    assert concepts[0].confidence == 0.8


def test_evidence_type_creates_low_risk_candidate_when_no_alias_matches():
    concepts = extract_company_concepts(
        _evidence(
            EvidenceType.LOCATION,
            "Hannover und Berlin.",
            title="Standorte",
        )
    )

    assert any(
        concept.concept_type == "location"
        and concept.canonical_value == "Standorte"
        for concept in concepts
    )


def test_company_taxonomy_expansion_covers_target_domains():
    concepts = extract_company_concepts(
        _evidence(
            EvidenceType.KRITIS,
            (
                "DB InfraGO betreibt Bahninfrastruktur und Schienenverkehr. "
                "Amprion arbeitet am Uebertragungsnetz und an der Energiewende. "
                "Dataport steht fuer Verwaltungsdigitalisierung und e-government. "
                "KWS verbindet Saatgut, Pflanzenzuechtung und digital farming."
            ),
        )
    )
    pairs = {
        (
            concept.concept_type,
            concept.canonical_value,
        )
        for concept in concepts
    }

    assert (
        "company_domain",
        "Rail Infrastructure",
    ) in pairs
    assert (
        "company_domain",
        "Transmission Grid",
    ) in pairs
    assert (
        "company_domain",
        "Public Sector Digitalization",
    ) in pairs
    assert (
        "company_domain",
        "Plant Breeding",
    ) in pairs
    assert (
        "company_domain",
        "Agricultural Digitalization",
    ) in pairs
