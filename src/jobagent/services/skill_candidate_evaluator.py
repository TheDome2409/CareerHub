import json
import re
from dataclasses import dataclass

from ollama import chat

from jobagent.services.skill_candidate_canonicalizer import (
    deduplicate_evaluations,
)
from jobagent.services.skill_candidate_domain_service import (
    detect_candidate_domain,
    normalize_candidate_domain,
)
from jobagent.services.taxonomy_loader import load_taxonomy


MODEL = "qwen3:30b"
MAX_CANDIDATES = 40
MAX_CONTEXT_CHARS = 5000
JSON_PREFIX = "["
LAST_EVALUATOR_DEBUG = ""


@dataclass
class SkillCandidateEvaluation:
    name: str
    is_skill: bool
    suggested_tag: str
    category: str
    weight: int
    confidence: float
    reason: str
    candidate_type: str = "unknown"
    canonical_name: str = ""
    source_type: str = "profile_document"
    document_source: str = ""
    job_title: str = ""
    company: str = ""
    job_source: str = ""
    job_url: str = ""
    candidate_domain: str = "unknown"
    accepted: bool = True


def _known_taxonomy_summary() -> str:
    taxonomy = load_taxonomy()
    lines = []

    for tag, data in sorted(taxonomy.items()):
        keywords = ", ".join(
            data.get("keywords", [])[:8]
        )
        label = data.get("label", tag)
        lines.append(
            f"- {tag}: {label} ({keywords})"
        )

    return "\n".join(lines)


def _response_content(response) -> str:
    message = getattr(response, "message", None)

    if message is not None:
        content = getattr(message, "content", None)

        if content:
            return content

        if isinstance(message, dict):
            return message.get("content") or ""

    if isinstance(response, dict):
        message = response.get("message")

        if isinstance(message, dict):
            return message.get("content") or ""

    return ""


def _set_debug(message: str) -> None:
    global LAST_EVALUATOR_DEBUG
    LAST_EVALUATOR_DEBUG = message


def last_skill_evaluator_debug() -> str:
    return LAST_EVALUATOR_DEBUG


def _json_payload(content: str):
    content = content.strip()

    if content.startswith("```"):
        content = re.sub(
            r"^```(?:json)?\s*",
            "",
            content,
            flags=re.IGNORECASE,
        )
        content = re.sub(
            r"\s*```$",
            "",
            content,
        )

    decoder = json.JSONDecoder()
    payloads = []
    index = 0

    while index < len(content):
        while (
            index < len(content)
            and content[index] not in "[{"
        ):
            index += 1

        if index >= len(content):
            break

        try:
            payload, next_index = decoder.raw_decode(
                content,
                index,
            )
        except json.JSONDecodeError:
            index += 1
            continue

        if isinstance(payload, list):
            payloads.extend(payload)
        elif isinstance(payload, dict):
            payloads.append(payload)

        index = next_index

    if payloads:
        return payloads

    return []


def _as_weight(value) -> int:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 5

    if 0 < numeric <= 1:
        numeric *= 10

    weight = int(round(numeric))

    return max(
        0,
        min(
            10,
            weight,
        ),
    )


def _as_confidence(value) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.5

    return max(
        0.0,
        min(
            1.0,
            confidence,
        ),
    )


def _as_bool(value, default: bool = True) -> bool:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {
        "1",
        "true",
        "yes",
        "ja",
        "y",
    }


def _slug(value: str) -> str:
    value = (value or "").strip().lower()
    value = value.replace("ä", "ae")
    value = value.replace("ö", "oe")
    value = value.replace("ü", "ue")
    value = value.replace("ß", "ss")
    value = value.replace("ä", "ae")
    value = value.replace("ö", "oe")
    value = value.replace("ü", "ue")
    value = value.replace("ß", "ss")
    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value,
    )

    return value.strip("_")


def _parse_evaluations(content: str) -> list[SkillCandidateEvaluation]:
    try:
        data = _json_payload(content)
    except Exception as error:
        _set_debug(
            f"parse_error={error}; raw={content[:1000]}"
        )
        return []

    evaluations = []

    for item in data:
        if not isinstance(item, dict):
            continue

        name = str(item.get("name") or "").strip()

        if not name:
            continue

        is_skill = _as_bool(
            item.get("is_skill"),
            True,
        )

        suggested_tag = _slug(
            item.get("suggested_tag") or name
        )
        category = _slug(
            item.get("category") or "unknown"
        ) or "unknown"

        evaluations.append(
            SkillCandidateEvaluation(
                name=name,
                is_skill=is_skill,
                suggested_tag=suggested_tag,
                category=category,
                weight=_as_weight(
                    item.get("weight")
                ),
                confidence=_as_confidence(
                    item.get("confidence")
                ),
                reason=str(
                    item.get("reason") or ""
                ).strip(),
                candidate_type=str(
                    item.get("candidate_type")
                    or "unknown"
                ).strip(),
                canonical_name=str(
                    item.get("canonical_name")
                    or name
                ).strip(),
                source_type=str(
                    item.get("source_type")
                    or "profile_document"
                ).strip(),
                document_source=str(
                    item.get("document_source")
                    or ""
                ).strip(),
                job_title=str(
                    item.get("job_title")
                    or ""
                ).strip(),
                company=str(
                    item.get("company")
                    or ""
                ).strip(),
                job_source=str(
                    item.get("job_source")
                    or ""
                ).strip(),
                job_url=str(
                    item.get("job_url")
                    or ""
                ).strip(),
                candidate_domain=normalize_candidate_domain(
                    item.get("candidate_domain")
                ),
                accepted=bool(
                    is_skill
                ),
            )
        )

    _set_debug(
        f"parsed={len(evaluations)}; raw_length={len(content)}"
    )

    return deduplicate_evaluations(
        evaluations
    )


def evaluate_unknown_skill_candidates(
    candidates: list[str],
    context_text: str,
    document_sources: dict[str, list[str]] | None = None,
    source_type: str = "profile_document",
    candidate_metadata: dict[str, dict] | None = None,
) -> list[SkillCandidateEvaluation]:
    candidates = [
        candidate
        for candidate in candidates[:MAX_CANDIDATES]
        if candidate and candidate.strip()
    ]

    if not candidates:
        return []

    response = chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Du bewertest unbekannte Skill-Kandidaten aus "
                    "Bewerbungsunterlagen oder Stellenanzeigen. "
                    "Antworte ausschliesslich "
                    "mit JSON. Keine Analyse, kein Markdown. "
                    "Fuehre das begonnene JSON-Array fort. "
                    "Erzeuge ein einziges JSON-Array, nicht mehrere. "
                    "Bewerte beruflich relevante Kompetenzen domänenneutral. "
                    "Dazu zählen je nach Domäne fachliche Skills, Methoden, "
                    "Verfahren, Standards, Fachprozesse, Tools/Systeme, "
                    "Frameworks, Zertifikate, Rollen und Technologiekompetenzen. "
                    "Pflegefachliche und pädagogische Methoden wie Basale "
                    "Stimulation, Kinästhetik oder Marte Meo gelten als "
                    "beruflich relevante Kompetenzen. Finanzwerkzeuge und "
                    "Fachprozesse wie DATEV, SAP FI, Kreditorenbuchhaltung "
                    "oder Kontenabstimmung gelten ebenfalls als beruflich "
                    "relevante Kompetenzen. Sortiere allgemeine Substantive, "
                    "Floskeln, Orte, Arbeitgeber, Dokumentbegriffe und isolierte "
                    "Kontextbegriffe aus. Klassifiziere Rollen, Zertifikate und "
                    "Kontextbegriffe separat. "
                    "Erfinde keine Nachweise."
                ),
            },
            {
                "role": "user",
                "content": f"""
Bestehende Taxonomie:
{_known_taxonomy_summary()}

Unknown Candidates:
{json.dumps(candidates, ensure_ascii=False)}

Dokumentquellen pro Candidate:
{json.dumps(document_sources or {}, ensure_ascii=False)}

Metadaten pro Candidate:
{json.dumps(candidate_metadata or {}, ensure_ascii=False)}

Kontextauszug:
{(context_text or "")[:MAX_CONTEXT_CHARS]}

Aufgabe:
Gib fuer geeignete Kandidaten eine Liste im Format zurueck:
[
  {{
    "name": "ERP-Releasewechsel",
    "is_skill": true,
    "suggested_tag": "erp_release_management",
    "category": "technical",
    "weight": 7,
    "confidence": 0.85,
    "reason": "Hinweis auf Erfahrung mit ERP-Releaseprozessen",
    "candidate_type": "skill",
    "canonical_name": "ERP Release Management",
    "source_type": "{source_type}",
    "document_source": "Lebenslauf.pdf",
    "job_title": "",
    "company": "",
    "job_source": "",
    "job_url": "",
    "candidate_domain": "it"
  }}
]

Regeln:
- Gib auch abgelehnte Kandidaten zurueck, aber mit "is_skill": false.
- suggested_tag muss snake_case sein.
- category: technical, leadership, project, consulting, social, domain oder other.
- weight 0 bis 10.
- confidence 0.0 bis 1.0.
- candidate_type: skill, role, certification, framework, regulation, context oder unknown.
- candidate_domain: it, finance, healthcare, education, public_service,
  legal, craft, general_business oder unknown.
- canonical_name ist der normalisierte Review-Begriff.
- Beispiele: Governance alleine -> context, NIS2 Compliance -> NIS2,
  GitOps Betriebsmodell -> GitOps, Zero Trust Strategie -> Zero Trust.
- Domain-Beispiele: Kreditorenbuchhaltung -> finance,
  Entlassungsmanagement -> healthcare, Sprachfoerderung -> education,
  Verwaltungsrecht -> legal, Fachverfahren -> public_service,
  Feuerstaettenschau -> craft, Azure Landing Zone -> it,
  Change Management -> general_business.
- source_type muss "{source_type}" sein.
- document_source und Job-Metadaten sollen nach Moeglichkeit aus den Quellen stammen.
- Maximal 20 Eintraege.
""",
            },
            {
                "role": "assistant",
                "content": JSON_PREFIX,
            },
        ],
        options={
            "temperature": 0.1,
            "num_predict": 1200,
        },
        think=False,
        keep_alive="30m",
    )

    raw_content = JSON_PREFIX + _response_content(
        response
    )
    _set_debug(
        f"raw_length={len(raw_content)}; raw={raw_content[:1000]}"
    )

    evaluations = _parse_evaluations(raw_content)

    if not evaluations:
        return []

    candidate_metadata = candidate_metadata or {}
    document_sources = document_sources or {}
    enriched = []

    for evaluation in evaluations:
        metadata = (
            candidate_metadata.get(evaluation.name)
            or candidate_metadata.get(evaluation.canonical_name)
            or {}
        )
        sources = document_sources.get(
            evaluation.name,
            document_sources.get(
                evaluation.canonical_name,
                [],
            ),
        )
        document_source = (
            evaluation.document_source
            or metadata.get("document_source")
            or ", ".join(sources)
        )
        candidate_domain = normalize_candidate_domain(
            evaluation.candidate_domain
        )

        if candidate_domain == "unknown":
            candidate_domain = detect_candidate_domain(
                evaluation.canonical_name or evaluation.name,
                context_text,
            )

        enriched.append(
            SkillCandidateEvaluation(
                name=evaluation.name,
                is_skill=evaluation.is_skill,
                suggested_tag=evaluation.suggested_tag,
                category=evaluation.category,
                weight=evaluation.weight,
                confidence=evaluation.confidence,
                reason=evaluation.reason,
                candidate_type=evaluation.candidate_type,
                canonical_name=evaluation.canonical_name,
                source_type=source_type,
                document_source=str(document_source or ""),
                job_title=str(metadata.get("job_title") or evaluation.job_title),
                company=str(metadata.get("company") or evaluation.company),
                job_source=str(metadata.get("job_source") or evaluation.job_source),
                job_url=str(metadata.get("job_url") or evaluation.job_url),
                candidate_domain=candidate_domain,
                accepted=evaluation.accepted,
            )
        )

    return deduplicate_evaluations(enriched)
