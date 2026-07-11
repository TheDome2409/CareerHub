import json

from jobagent.models.company_evidence import CompanyEvidence, EvidenceType
from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.company_knowledge_builder import build_company_knowledge
from jobagent.services.company_knowledge_review_service import (
    build_company_review_prompt,
    review_company_knowledge_draft,
    review_company_knowledge_draft_with_llm,
)


class FakeLlmClient:
    def __init__(self, payload: dict):
        self.payload = payload
        self.prompt = ""

    def complete(self, prompt: str) -> str:
        self.prompt = prompt

        return json.dumps(
            self.payload,
            ensure_ascii=False,
        )


class FakeJsonLlmClient:
    default_model = "qwen3:30b"

    def __init__(self, payload: dict):
        self.payload = payload
        self.system_prompt = ""
        self.user_prompt = ""
        self.last_model = self.default_model

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt

        return self.payload


class UnavailableOllama:
    def is_available(self) -> bool:
        return False


def _company(repository: CompanyRepository):
    return repository.upsert_company(
        "Dataport"
    )


def _evidence(
    repository: CompanyRepository,
    company_id: int,
    evidence_type,
    text: str,
    source_name: str = "Website",
    source_url: str = "https://example.test",
):
    return repository.save_company_evidence(
        CompanyEvidence(
            company_id=company_id,
            evidence_type=evidence_type,
            title=str(
                evidence_type.value
                if hasattr(evidence_type, "value")
                else evidence_type
            ),
            text=text,
            source_type="company_website",
            source_name=source_name,
            source_url=source_url,
            section=str(
                evidence_type.value
                if hasattr(evidence_type, "value")
                else evidence_type
            ),
            confidence=0.75,
        )
    )


def test_review_prompt_contains_grouped_evidence_and_ids(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = _company(
        repository
    )
    mission = _evidence(
        repository,
        company.id,
        EvidenceType.MISSION,
        "Wir digitalisieren Verwaltung.",
    )
    build_company_knowledge(
        company.id,
        repository=repository,
    )
    client = FakeLlmClient(
        {
            "mission": "Digitalisierung der Verwaltung.",
            "confidence": 0.7,
            "source_evidence_ids": [
                mission.id,
            ],
        }
    )

    review_company_knowledge_draft_with_llm(
        company.id,
        llm_client=client,
        repository=repository,
    )

    assert "evidence_by_type" in client.prompt
    assert "mission" in client.prompt
    assert str(mission.id) in client.prompt
    assert "source_evidence_ids" in client.prompt


def test_prompt_builder_returns_json_only_prompt_with_evidence_ids(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = _company(
        repository
    )
    mission = _evidence(
        repository,
        company.id,
        EvidenceType.MISSION,
        "Wir digitalisieren Verwaltung.",
    )
    draft = build_company_knowledge(
        company.id,
        repository=repository,
    )
    system_prompt, user_prompt = build_company_review_prompt(
        draft,
        {
            "mission": [
                {
                    "id": mission.id,
                    "text": mission.text,
                }
            ]
        },
    )

    assert "JSON" in system_prompt
    assert "Markdown" in system_prompt
    assert "source_evidence_ids" in user_prompt
    assert str(mission.id) in user_prompt
    assert json.loads(user_prompt)["evidence_by_type"]["mission"][0]["id"] == mission.id


def test_review_json_is_persisted_as_company_knowledge_draft(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = _company(
        repository
    )
    mission = _evidence(
        repository,
        company.id,
        EvidenceType.MISSION,
        "Wir digitalisieren Verwaltung.",
    )
    _evidence(
        repository,
        company.id,
        EvidenceType.TECHNOLOGY,
        "Cloud und Data Analytics.",
    )
    build_company_knowledge(
        company.id,
        repository=repository,
    )
    client = FakeLlmClient(
        {
            "mission": "Digitalisierung der Verwaltung.",
            "vision": "Digitale Services für die öffentliche Hand.",
            "technologies": [
                "Cloud",
                "Data Analytics",
            ],
            "confidence": 0.82,
            "source_evidence_ids": [
                mission.id,
            ],
        }
    )

    draft = review_company_knowledge_draft(
        company.id,
        llm_client=client,
        repository=repository,
    )
    drafts = repository.list_company_knowledge_drafts(
        company.id
    )

    assert draft.mission == "Digitalisierung der Verwaltung."
    assert draft.vision == "Digitale Services für die öffentliche Hand."
    assert draft.technologies == [
        "Cloud",
        "Data Analytics",
    ]
    assert draft.confidence == 0.82
    assert draft.review_method == "llm_reviewed"
    assert len(drafts) == 2
    assert repository.load_latest_company_knowledge_draft(
        company.id
    ).id == draft.id


def test_review_generate_json_client_persists_model_name(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = _company(
        repository
    )
    mission = _evidence(
        repository,
        company.id,
        EvidenceType.MISSION,
        "Wir digitalisieren Verwaltung.",
    )
    build_company_knowledge(
        company.id,
        repository=repository,
    )
    client = FakeJsonLlmClient(
        {
            "mission": "Digitalisierung der Verwaltung.",
            "confidence": 0.81,
            "source_evidence_ids": [
                mission.id,
            ],
        }
    )

    draft = review_company_knowledge_draft(
        company.id,
        llm_client=client,
        repository=repository,
    )

    assert draft.review_method == "llm_reviewed"
    assert draft.review_model == "qwen3:30b"
    assert "evidence_by_type" in client.user_prompt
    assert draft.mission == "Digitalisierung der Verwaltung."


def test_review_filters_evidence_ids_without_source(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = _company(
        repository
    )
    sourced = _evidence(
        repository,
        company.id,
        EvidenceType.MISSION,
        "Sourced Mission.",
    )
    unsourced = _evidence(
        repository,
        company.id,
        EvidenceType.VISION,
        "Unsourced Vision.",
        source_name="",
        source_url="",
    )
    build_company_knowledge(
        company.id,
        repository=repository,
    )
    client = FakeLlmClient(
        {
            "mission": "Sourced Mission.",
            "source_evidence_ids": [
                sourced.id,
                unsourced.id,
                9999,
            ],
        }
    )

    draft = review_company_knowledge_draft(
        company.id,
        llm_client=client,
        repository=repository,
    )

    assert draft.source_evidence_ids == [
        sourced.id,
    ]


def test_review_fallback_without_llm_returns_rule_based_draft(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "jobagent.services.company_knowledge_review_service.OllamaClient",
        lambda: UnavailableOllama(),
    )
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = _company(
        repository
    )
    _evidence(
        repository,
        company.id,
        EvidenceType.MISSION,
        "Wir digitalisieren Verwaltung.",
    )
    existing = build_company_knowledge(
        company.id,
        repository=repository,
    )

    draft = review_company_knowledge_draft(
        company.id,
        repository=repository,
    )
    drafts = repository.list_company_knowledge_drafts(
        company.id
    )

    assert draft.id == existing.id
    assert draft.mission == existing.mission
    assert draft.review_method == "rule_based"
    assert draft.review_notes
    assert len(drafts) == 1


def test_review_fallback_builds_rule_based_draft_if_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "jobagent.services.company_knowledge_review_service.OllamaClient",
        lambda: UnavailableOllama(),
    )
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = _company(
        repository
    )
    _evidence(
        repository,
        company.id,
        EvidenceType.MISSION,
        "Wir digitalisieren Verwaltung.",
    )

    draft = review_company_knowledge_draft(
        company.id,
        repository=repository,
    )

    assert draft.mission == "Wir digitalisieren Verwaltung."
    assert draft.review_method == "rule_based"
    assert len(
        repository.list_company_knowledge_drafts(
            company.id
        )
    ) == 1


def test_review_invalid_json_falls_back_without_new_draft(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = _company(
        repository
    )
    _evidence(
        repository,
        company.id,
        EvidenceType.MISSION,
        "Wir digitalisieren Verwaltung.",
    )
    existing = build_company_knowledge(
        company.id,
        repository=repository,
    )

    class InvalidClient:
        def complete(self, prompt: str) -> str:
            return "not json"

    draft = review_company_knowledge_draft(
        company.id,
        llm_client=InvalidClient(),
        repository=repository,
    )

    assert draft.id == existing.id
    assert draft.review_method == "rule_based"
    assert draft.review_notes
    assert len(repository.list_company_knowledge_drafts(company.id)) == 1
