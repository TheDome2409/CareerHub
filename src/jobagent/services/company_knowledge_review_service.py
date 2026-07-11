import json
import logging
import re
import time

from jobagent.models.company_knowledge_draft import CompanyKnowledgeDraft
from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.company_knowledge_builder import build_company_knowledge
from jobagent.services.ollama_client import OllamaClient


logger = logging.getLogger(__name__)


def _repository(repository: CompanyRepository | None = None) -> CompanyRepository:
    return repository or CompanyRepository()


def _value(value) -> str:
    return str(value.value if hasattr(value, "value") else value)


def _group_evidence(evidence_items) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}

    for evidence in evidence_items:
        evidence_type = _value(evidence.evidence_type)
        grouped.setdefault(evidence_type, []).append(
            {
                "id": evidence.id,
                "document_id": evidence.document_id,
                "title": evidence.title,
                "text": evidence.text,
                "source_type": evidence.source_type,
                "source_name": evidence.source_name,
                "source_url": evidence.source_url,
                "section": evidence.section,
                "confidence": evidence.confidence,
            }
        )

    return grouped


def _review_payload(
    existing_draft: CompanyKnowledgeDraft,
    grouped_evidence: dict[str, list[dict]],
) -> dict:
    return {
        "task": "Review and improve a CompanyKnowledgeDraft using only evidence.",
        "rules": [
            "Use only information present in evidence.",
            "Do not invent facts, sources, products, technologies, benefits, or locations.",
            "Remove duplicates and lower confidence for uncertain information.",
            "Return JSON only.",
            "Only use source_evidence_ids that are present in the evidence input.",
        ],
        "draft": existing_draft.to_dict(),
        "evidence_by_type": grouped_evidence,
        "expected_output_fields": [
            "mission",
            "vision",
            "culture",
            "business_domains",
            "mission_keywords",
            "industries",
            "technologies",
            "work_models",
            "locations",
            "innovation_areas",
            "benefits",
            "kritis_relevance",
            "confidence",
            "source_evidence_ids",
        ],
    }


def build_company_review_prompt(
    existing_draft: CompanyKnowledgeDraft,
    grouped_evidence: dict[str, list[dict]],
) -> tuple[str, str]:
    payload = _review_payload(existing_draft, grouped_evidence)
    system_prompt = (
        "Du bist ein vorsichtiger Company Knowledge Reviewer. "
        "Verbessere den Draft ausschließlich anhand der Evidence. "
        "Erfinde keine Fakten, Quellen, Produkte, Technologien, Benefits "
        "oder Standorte. Gib ausschließlich valides JSON zurück. "
        "Keine Markdown-Blöcke, keine Erklärungen."
    )
    user_prompt = json.dumps(payload, ensure_ascii=False, indent=2)

    return system_prompt, user_prompt


def _combined_prompt(system_prompt: str, user_prompt: str) -> str:
    return f"{system_prompt}\n\n{user_prompt}"


def _resolve_llm_client(llm_client):
    if llm_client is not None:
        return llm_client

    try:
        ollama_client = OllamaClient()
    except Exception as exc:
        logger.info("Ollama client initialization failed: %s", exc)
        return None

    if not ollama_client.is_available():
        logger.info("Ollama is not available, using rule-based fallback.")
        return None

    return ollama_client


def _client_model_name(llm_client) -> str | None:
    return (
        getattr(llm_client, "last_model", None)
        or getattr(llm_client, "default_model", None)
        or getattr(llm_client, "model", None)
    )


def _call_llm(llm_client, prompt: str):
    if llm_client is None:
        return None

    if hasattr(llm_client, "review_company_knowledge"):
        return llm_client.review_company_knowledge(prompt)

    if hasattr(llm_client, "complete"):
        return llm_client.complete(prompt)

    if hasattr(llm_client, "generate"):
        return llm_client.generate(prompt)

    if callable(llm_client):
        return llm_client(prompt)

    return None


def _call_json_llm(llm_client, system_prompt: str, user_prompt: str):
    if llm_client is None:
        return None

    if hasattr(llm_client, "generate_json"):
        return llm_client.generate_json(system_prompt, user_prompt)

    return _call_llm(llm_client, _combined_prompt(system_prompt, user_prompt))


def _parse_json_response(response) -> dict | None:
    if response is None:
        return None

    if isinstance(response, dict):
        return response

    if hasattr(response, "content"):
        response = response.content

    text = str(response).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)

    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _allowed_evidence_ids(evidence_items) -> set[int]:
    return {
        int(evidence.id)
        for evidence in evidence_items
        if evidence.id is not None
        and (str(evidence.source_name or "").strip() or str(evidence.source_url or "").strip())
    }


def _source_documents_for_ids(evidence_items, evidence_ids: list[int]) -> list[int]:
    selected = {int(evidence_id) for evidence_id in evidence_ids}

    return sorted(
        {
            int(evidence.document_id)
            for evidence in evidence_items
            if evidence.id in selected and evidence.document_id is not None
        }
    )


def _list_value(data: dict, key: str) -> list[str]:
    value = data.get(key, [])

    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]

    if value:
        return [str(value)]

    return []


def _draft_from_llm_data(
    company_id: int,
    data: dict,
    evidence_items,
    fallback: CompanyKnowledgeDraft,
    review_model: str | None = None,
) -> CompanyKnowledgeDraft:
    allowed_ids = _allowed_evidence_ids(evidence_items)
    evidence_ids = [
        int(evidence_id)
        for evidence_id in data.get(
            "source_evidence_ids",
            fallback.source_evidence_ids,
        )
        if int(evidence_id) in allowed_ids
    ]

    return CompanyKnowledgeDraft(
        company_id=company_id,
        mission=data.get("mission", fallback.mission),
        vision=data.get("vision", fallback.vision),
        culture=data.get("culture", fallback.culture),
        business_domains=_list_value(data, "business_domains") or fallback.business_domains,
        mission_keywords=_list_value(data, "mission_keywords") or fallback.mission_keywords,
        industries=_list_value(data, "industries") or fallback.industries,
        technologies=_list_value(data, "technologies") or fallback.technologies,
        work_models=_list_value(data, "work_models") or fallback.work_models,
        locations=_list_value(data, "locations") or fallback.locations,
        innovation_areas=_list_value(data, "innovation_areas") or fallback.innovation_areas,
        benefits=_list_value(data, "benefits") or fallback.benefits,
        kritis_relevance=bool(data.get("kritis_relevance", fallback.kritis_relevance)),
        confidence=float(data.get("confidence", fallback.confidence) or 0.0),
        evidence_count=len(evidence_items),
        source_documents=_source_documents_for_ids(evidence_items, evidence_ids)
        or fallback.source_documents,
        source_evidence_ids=evidence_ids or fallback.source_evidence_ids,
        canonical_concepts=_list_value(data, "canonical_concepts")
        or fallback.canonical_concepts,
        concept_statistics=data.get("concept_statistics")
        or fallback.concept_statistics,
        review_method="llm_reviewed",
        review_model=review_model,
    )


def _current_or_rule_based_draft(
    company_id: int,
    repository: CompanyRepository,
) -> CompanyKnowledgeDraft:
    existing = repository.load_latest_company_knowledge_draft(company_id)

    if existing is not None:
        return existing

    return build_company_knowledge(company_id, repository=repository)


def review_company_knowledge_draft(
    company_id: int,
    llm_client=None,
    repository: CompanyRepository | None = None,
) -> CompanyKnowledgeDraft:
    return review_company_knowledge_draft_with_llm(
        company_id,
        llm_client=llm_client,
        repository=repository,
    )


def review_company_knowledge_draft_with_llm(
    company_id: int,
    llm_client=None,
    repository: CompanyRepository | None = None,
) -> CompanyKnowledgeDraft:
    repo = _repository(repository)
    existing_draft = _current_or_rule_based_draft(company_id, repo)
    evidence_items = repo.list_company_evidence(company_id)
    grouped = _group_evidence(evidence_items)
    system_prompt, user_prompt = build_company_review_prompt(existing_draft, grouped)
    resolved_client = _resolve_llm_client(llm_client)

    if resolved_client is None:
        logger.info(
            "Company knowledge draft review fallback for company_id=%s: no LLM client",
            company_id,
        )
        existing_draft.review_notes = "LLM nicht verfügbar oder keine gültige JSON-Antwort."

        return existing_draft

    started = time.perf_counter()

    try:
        response = _call_json_llm(resolved_client, system_prompt, user_prompt)
    except Exception as exc:
        logger.warning(
            "Company knowledge draft LLM review failed for company_id=%s: %s",
            company_id,
            exc,
        )
        existing_draft.review_notes = "LLM nicht verfügbar oder keine gültige JSON-Antwort."

        return existing_draft

    logger.info(
        "Company knowledge draft LLM review completed company_id=%s duration_ms=%s",
        company_id,
        int((time.perf_counter() - started) * 1000),
    )

    data = _parse_json_response(response)

    if not data:
        logger.warning(
            "Company knowledge draft LLM review returned invalid JSON for company_id=%s",
            company_id,
        )
        logger.info(
            "Company knowledge draft review fallback for company_id=%s",
            company_id,
        )
        existing_draft.review_notes = "LLM nicht verfügbar oder keine gültige JSON-Antwort."

        return existing_draft

    reviewed = _draft_from_llm_data(
        company_id,
        data,
        evidence_items,
        existing_draft,
        review_model=_client_model_name(resolved_client),
    )

    return repo.save_company_knowledge_draft(reviewed)
