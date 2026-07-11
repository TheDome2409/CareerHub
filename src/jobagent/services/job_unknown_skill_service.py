from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from jobagent.services.review_queue_service import add_review_candidates
from jobagent.services.skill_candidate_canonicalizer import (
    classify_candidate_type,
    normalize_candidate,
)
from jobagent.services.unknown_skill_service import (
    detect_unknown_skill_candidates,
)

if TYPE_CHECKING:
    from jobagent.services.skill_candidate_evaluator import (
        SkillCandidateEvaluation,
    )


MAX_JOB_TEXT_CHARS = 3500
DEFAULT_JOB_LIMIT = 10
UNWANTED_JOB_TERMS = {
    "arbeitszeit",
    "attraktives gehalt",
    "benefits",
    "cloud platform engineer",
    "erfahrung",
    "flache hierarchien",
    "homeoffice",
    "kommunikation",
    "m w d",
    "spannende aufgaben",
    "standort",
    "teamfaehigkeit",
    "teamfahigkeit",
    "teilzeit",
    "vollzeit",
    "wir suchen",
}


@dataclass
class JobUnknownSkillResult:
    candidates: list[str]
    evaluations: list[SkillCandidateEvaluation]
    review_queue: list[dict]
    analyzed_jobs: int
    queued_count: int
    context_text: str
    evaluator_debug: str = ""
    used_fallback: bool = False


def _value_to_text(value) -> str:
    if value is None:
        return ""

    if isinstance(value, (list, tuple, set)):
        return "\n".join(
            str(item)
            for item in value
            if item
        )

    return str(value)


def job_document_source(job) -> str:
    title = getattr(job, "title", "") or "Unbekannte Stelle"
    company = getattr(job, "company", "") or "Arbeitgeber unbekannt"
    source = (
        getattr(job, "source_name", None)
        or getattr(job, "source_type", None)
        or "Job"
    )

    return f"{source}: {title} | {company}"


def job_metadata(job) -> dict:
    return {
        "source_type": "job_posting",
        "document_source": job_document_source(job),
        "job_title": getattr(job, "title", "") or "",
        "company": getattr(job, "company", "") or "",
        "job_source": (
            getattr(job, "source_name", None)
            or getattr(job, "source_type", None)
            or ""
        ),
        "job_url": getattr(job, "url", "") or "",
    }


def job_text(job) -> str:
    fields = [
        "title",
        "company",
        "location",
        "description",
        "requirements",
        "responsibilities",
        "skills",
        "raw_text",
    ]
    parts = []

    for field in fields:
        if hasattr(job, field):
            text = _value_to_text(
                getattr(job, field)
            ).strip()

            if text:
                parts.append(text)

    return "\n".join(parts)[:MAX_JOB_TEXT_CHARS]


def _candidate_allowed(candidate: str, job) -> bool:
    normalized = normalize_candidate(candidate)

    if not normalized:
        return False

    if normalized in UNWANTED_JOB_TERMS:
        return False

    title = normalize_candidate(
        getattr(job, "title", "") or ""
    )

    if normalized == title:
        return False

    candidate_type = classify_candidate_type(candidate)

    if candidate_type in {"role", "context", "unknown"}:
        return False

    return True


def extract_job_unknown_skill_candidates(
    jobs,
    limit: int = DEFAULT_JOB_LIMIT,
) -> tuple[list[str], str, dict[str, list[str]], dict[str, dict], int]:
    selected_jobs = list(jobs or [])[:limit]
    candidates_by_name: dict[str, str] = {}
    document_sources: dict[str, list[str]] = {}
    candidate_metadata: dict[str, dict] = {}
    context_parts = []

    for job in selected_jobs:
        text = job_text(job)

        if not text:
            continue

        context_parts.append(text)
        metadata = job_metadata(job)

        for candidate in detect_unknown_skill_candidates(text):
            if not _candidate_allowed(candidate, job):
                continue

            normalized = normalize_candidate(candidate)
            candidates_by_name.setdefault(
                normalized,
                candidate,
            )
            display_name = candidates_by_name[normalized]
            document_sources.setdefault(
                display_name,
                [],
            )

            if metadata["document_source"] not in document_sources[display_name]:
                document_sources[display_name].append(
                    metadata["document_source"]
                )

            candidate_metadata.setdefault(
                display_name,
                metadata,
            )

    candidates = list(
        candidates_by_name.values()
    )

    return (
        candidates,
        "\n\n".join(context_parts),
        document_sources,
        candidate_metadata,
        len(selected_jobs),
    )


def _fallback_evaluations(
    candidates: list[str],
    document_sources: dict[str, list[str]],
    candidate_metadata: dict[str, dict],
) -> list[SkillCandidateEvaluation]:
    from jobagent.services.skill_candidate_evaluator import (
        SkillCandidateEvaluation,
    )

    evaluations = []

    for candidate in candidates:
        metadata = candidate_metadata.get(
            candidate,
            {},
        )
        sources = document_sources.get(
            candidate,
            [],
        )

        evaluations.append(
            SkillCandidateEvaluation(
                name=candidate,
                is_skill=True,
                suggested_tag="",
                category="technical",
                weight=5,
                confidence=0.55,
                reason=(
                    "Heuristisch aus Stellenanzeige erkannt; "
                    "LLM-Bewertung hat keinen Eintrag geliefert."
                ),
                candidate_type="skill",
                canonical_name=candidate,
                source_type="job_posting",
                document_source=(
                    metadata.get("document_source")
                    or ", ".join(sources)
                ),
                job_title=metadata.get("job_title") or "",
                company=metadata.get("company") or "",
                job_source=metadata.get("job_source") or "",
                job_url=metadata.get("job_url") or "",
            )
        )

    return evaluations


def detect_job_unknown_skills(
    jobs,
    limit: int = DEFAULT_JOB_LIMIT,
) -> JobUnknownSkillResult:
    from jobagent.services.skill_candidate_evaluator import (
        evaluate_unknown_skill_candidates,
        last_skill_evaluator_debug,
    )

    (
        candidates,
        context_text,
        document_sources,
        candidate_metadata,
        analyzed_jobs,
    ) = extract_job_unknown_skill_candidates(
        jobs,
        limit=limit,
    )

    evaluations = evaluate_unknown_skill_candidates(
        candidates,
        context_text,
        document_sources=document_sources,
        source_type="job_posting",
        candidate_metadata=candidate_metadata,
    )
    used_fallback = False

    if candidates and not evaluations:
        evaluations = _fallback_evaluations(
            candidates,
            document_sources,
            candidate_metadata,
        )
        used_fallback = True

    review_queue = add_review_candidates(
        evaluations
    )

    return JobUnknownSkillResult(
        candidates=candidates,
        evaluations=evaluations,
        review_queue=review_queue,
        analyzed_jobs=analyzed_jobs,
        queued_count=len(evaluations),
        context_text=context_text,
        evaluator_debug=last_skill_evaluator_debug(),
        used_fallback=used_fallback,
    )
