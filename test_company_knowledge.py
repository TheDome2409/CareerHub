from jobagent.models.company_enums import (
    BusinessDomain,
    WorkModel,
)
from jobagent.models.company_knowledge import CompanyKnowledge
from jobagent.services.company_knowledge_mapper import (
    normalize_business_domain,
    normalize_location,
    normalize_technology,
    normalize_work_model,
)


def _kws_knowledge() -> CompanyKnowledge:
    return CompanyKnowledge(
        mission="Innovative Pflanzenzüchtung für nachhaltige Landwirtschaft.",
        business_domains=[
            BusinessDomain.RESEARCH,
            "agriculture",
        ],
        work_models=[
            WorkModel.HYBRID,
        ],
        innovation_areas=[
            "digital farming",
            "plant breeding",
        ],
        critical_infrastructure=False,
        technologies=[
            "SAP",
            "Azure",
            "Data Analytics",
        ],
        confidence=0.8,
    )


def test_company_knowledge_model_can_be_created():
    knowledge = _kws_knowledge()

    assert knowledge.mission.startswith("Innovative")
    assert knowledge.business_domains == [
        BusinessDomain.RESEARCH,
        "agriculture",
    ]
    assert knowledge.work_models == [
        WorkModel.HYBRID,
    ]
    assert knowledge.critical_infrastructure is False
    assert knowledge.confidence == 0.8
    assert knowledge.created_at


def test_company_knowledge_serializes_lists_and_enums():
    data = _kws_knowledge().to_dict()

    assert data["business_domains"] == [
        "research",
        "agriculture",
    ]
    assert data["work_models"] == [
        "hybrid",
    ]
    assert data["innovation_areas"] == [
        "digital farming",
        "plant breeding",
    ]
    assert data["technologies"] == [
        "SAP",
        "Azure",
        "Data Analytics",
    ]


def test_company_knowledge_json_roundtrip():
    original = _kws_knowledge()
    restored = CompanyKnowledge.from_dict(
        original.to_dict()
    )

    assert restored.to_dict() == original.to_dict()


def test_company_knowledge_from_dict_accepts_llm_like_payload():
    payload = {
        "mission": "Seeds and digital agriculture.",
        "business_domains": [
            "agriculture",
            "research",
        ],
        "work_models": [
            "hybrid",
        ],
        "critical_infrastructure": False,
        "technologies": [
            "SAP",
            "Azure",
        ],
    }

    knowledge = CompanyKnowledge.from_dict(
        payload
    )

    assert knowledge.mission == "Seeds and digital agriculture."
    assert knowledge.business_domains == [
        "agriculture",
        BusinessDomain.RESEARCH,
    ]
    assert knowledge.work_models == [
        WorkModel.HYBRID,
    ]


def test_company_knowledge_mapping_functions_normalize_values():
    assert normalize_work_model("Home Office") == "remote"
    assert normalize_work_model(WorkModel.HYBRID) == "hybrid"
    assert normalize_business_domain("Öffentlicher Dienst") == "public_sector"
    assert normalize_business_domain(BusinessDomain.ENERGY) == "energy"
    assert normalize_business_domain("Landwirtschaft") == "agriculture"
    assert normalize_technology("microsoft azure") == "Azure"
    assert normalize_technology("SAP") == "SAP"
    assert normalize_location("  Einbeck   ") == "Einbeck"
