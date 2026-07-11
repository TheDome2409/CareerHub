from jobagent.models.company_evidence import CompanyEvidence, EvidenceType
from jobagent.models.company_knowledge_draft import CompanyKnowledgeDraft
from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.company_knowledge_builder import (
    build_company_knowledge,
    list_company_knowledge_drafts,
    load_latest_company_knowledge_draft,
)
from jobagent.services.companyhub_db_service import get_connection


def _company(repository: CompanyRepository):
    return repository.upsert_company(
        "Dataport"
    )


def _save_evidence(
    repository: CompanyRepository,
    company_id: int,
    evidence_type,
    text: str,
    document_id: int | None = None,
):
    return repository.save_company_evidence(
        CompanyEvidence(
            company_id=company_id,
            document_id=document_id,
            evidence_type=evidence_type,
            title=str(
                evidence_type.value
                if hasattr(evidence_type, "value")
                else evidence_type
            ),
            text=text,
            source_type="company_website",
            source_name="Website",
            source_url="https://example.test",
            section=str(
                evidence_type.value
                if hasattr(evidence_type, "value")
                else evidence_type
            ),
            confidence=0.75,
        )
    )


def test_company_knowledge_draft_model_roundtrip():
    draft = CompanyKnowledgeDraft(
        company_id=1,
        mission="Mission",
        technologies=[
            "Cloud",
        ],
        confidence=0.8,
        evidence_count=2,
        source_documents=[
            1,
        ],
        source_evidence_ids=[
            10,
            11,
        ],
    )

    loaded = CompanyKnowledgeDraft.from_dict(
        draft.to_dict()
    )

    assert loaded.company_id == 1
    assert loaded.mission == "Mission"
    assert loaded.technologies == [
        "Cloud",
    ]
    assert loaded.mission_keywords == []
    assert loaded.industries == []
    assert loaded.canonical_concepts == []


def test_build_company_knowledge_uses_mission_and_vision(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = _company(
        repository
    )
    mission = _save_evidence(
        repository,
        company.id,
        EvidenceType.MISSION,
        "Wir digitalisieren Verwaltung.",
    )
    vision = _save_evidence(
        repository,
        company.id,
        EvidenceType.VISION,
        "Digitale Infrastruktur für alle.",
    )

    draft = build_company_knowledge(
        company.id,
        repository=repository,
    )

    assert draft.mission == "Wir digitalisieren Verwaltung."
    assert draft.vision == "Digitale Infrastruktur für alle."
    assert draft.evidence_count == 2
    assert draft.source_documents == []
    assert draft.source_evidence_ids == [
        mission.id,
        vision.id,
    ]


def test_build_company_knowledge_collects_technologies_and_benefits(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = _company(
        repository
    )
    _save_evidence(
        repository,
        company.id,
        EvidenceType.TECHNOLOGY,
        "Microsoft Azure und Data Analytics",
    )
    _save_evidence(
        repository,
        company.id,
        EvidenceType.TECHNOLOGY,
        "Azure Cloud und Data Analytics",
    )
    _save_evidence(
        repository,
        company.id,
        EvidenceType.BENEFIT,
        "Flexible Arbeitszeiten und Weiterbildung",
    )

    draft = build_company_knowledge(
        company.id,
        repository=repository,
    )

    assert draft.technologies == [
        "Azure",
        "Data Analytics",
    ]
    assert draft.benefits == [
        "Flexible Working Hours",
        "Professional Development",
    ]
    assert draft.concept_statistics["merged"] >= 1


def test_build_company_knowledge_collects_work_models_and_kritis(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = _company(
        repository
    )
    _save_evidence(
        repository,
        company.id,
        EvidenceType.REMOTE,
        "Remote möglich",
    )
    _save_evidence(
        repository,
        company.id,
        EvidenceType.HYBRID,
        "Hybrid möglich",
    )
    _save_evidence(
        repository,
        company.id,
        EvidenceType.KRITIS,
        "Kritische Infrastruktur",
    )

    draft = build_company_knowledge(
        company.id,
        repository=repository,
    )

    assert draft.work_models == [
        "Hybrid",
        "Remote",
    ]
    assert draft.kritis_relevance is True
    assert "kritis:Critical Infrastructure" in draft.canonical_concepts


def test_build_company_knowledge_handles_empty_evidence(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = _company(
        repository
    )

    draft = build_company_knowledge(
        company.id,
        repository=repository,
    )

    assert draft.mission is None
    assert draft.evidence_count == 0
    assert draft.confidence == 0.0
    assert draft.concept_statistics["total"] == 0


def test_company_knowledge_draft_repository_roundtrip(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = _company(
        repository
    )
    _save_evidence(
        repository,
        company.id,
        EvidenceType.BENEFIT,
        "Weiterbildung",
    )

    saved = build_company_knowledge(
        company.id,
        repository=repository,
    )
    latest = load_latest_company_knowledge_draft(
        company.id,
        repository=repository,
    )
    drafts = list_company_knowledge_drafts(
        company.id,
        repository=repository,
    )

    assert latest.id == saved.id
    assert len(drafts) == 1
    assert drafts[0].benefits == [
        "Professional Development",
    ]


def test_build_company_knowledge_maps_canonical_concepts_to_new_fields(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = _company(
        repository
    )
    _save_evidence(
        repository,
        company.id,
        EvidenceType.MISSION,
        "Wir treiben Digitalisierung und digitale Transformation.",
    )
    _save_evidence(
        repository,
        company.id,
        EvidenceType.BUSINESS_UNIT,
        "Digital Farming und digitale Landwirtschaft.",
    )
    _save_evidence(
        repository,
        company.id,
        EvidenceType.LOCATION,
        "Hannover.",
    )

    draft = build_company_knowledge(
        company.id,
        repository=repository,
    )

    assert draft.mission_keywords == [
        "Digital Transformation",
    ]
    assert draft.business_domains == [
        "Agricultural Digitalization",
    ]
    assert "mission_term:Digital Transformation" in draft.canonical_concepts
    assert draft.concept_statistics["canonical"] >= 2
    assert draft.source_evidence_ids


def test_company_knowledge_draft_table_exists(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )

    with get_connection(repository.db_path) as connection:
        row = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'company_knowledge_drafts'
            """
        ).fetchone()

    assert row["name"] == "company_knowledge_drafts"
