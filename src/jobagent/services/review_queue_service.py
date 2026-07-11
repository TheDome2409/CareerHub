from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from jobagent.repositories import JsonReviewQueueRepository


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REVIEW_QUEUE_FILE = PROJECT_ROOT / "data" / "review_queue.json"
VALID_STATUSES = {
    "pending",
    "approved",
    "rejected",
}


def _repository(
    path: str | Path | None = None,
) -> JsonReviewQueueRepository:
    return JsonReviewQueueRepository(
        path or REVIEW_QUEUE_FILE
    )


def load_review_queue() -> list[dict]:
    return _repository().load_entries()


def save_review_queue(items: list[dict]) -> None:
    _repository().save_entries(
        items
    )


def _queue_key(item: dict) -> tuple[str, str, str]:
    return (
        str(item.get("canonical_name") or "").lower(),
        str(item.get("suggested_tag") or "").lower(),
        str(item.get("candidate_type") or "").lower(),
    )


def review_item_key(item: dict) -> str:
    return "|".join(
        _queue_key(item)
    )


def _merge_sources(first: str, second: str) -> str:
    sources = []

    for value in [first, second]:
        for source in str(value or "").split(","):
            source = source.strip()

            if source and source not in sources:
                sources.append(source)

    return ", ".join(sources)


def _source_entry(item: dict) -> dict:
    return {
        "source_type": item.get("source_type") or "profile_document",
        "document_source": item.get("document_source") or "",
        "job_title": item.get("job_title") or "",
        "company": item.get("company") or "",
        "job_source": item.get("job_source") or "",
        "job_url": item.get("job_url") or "",
    }


def _source_key(source: dict) -> tuple[str, str, str, str, str]:
    return (
        str(source.get("source_type") or ""),
        str(source.get("document_source") or ""),
        str(source.get("job_title") or ""),
        str(source.get("company") or ""),
        str(source.get("job_url") or ""),
    )


def _normalized_sources(item: dict) -> list[dict]:
    sources = item.get("sources")

    if not isinstance(sources, list):
        sources = []

    normalized = []

    for source in sources:
        if isinstance(source, dict):
            normalized.append(
                {
                    "source_type": source.get("source_type") or "",
                    "document_source": source.get("document_source") or "",
                    "job_title": source.get("job_title") or "",
                    "company": source.get("company") or "",
                    "job_source": source.get("job_source") or "",
                    "job_url": source.get("job_url") or "",
                }
            )

    entry = _source_entry(item)

    if any(entry.values()):
        normalized.append(entry)

    merged = []
    seen = set()

    for source in normalized:
        key = _source_key(source)

        if key in seen:
            continue

        seen.add(key)
        merged.append(source)

    return merged


def _merge_source_lists(first: dict, second: dict) -> list[dict]:
    merged = []
    seen = set()

    for item in [first, second]:
        for source in _normalized_sources(item):
            key = _source_key(source)

            if key in seen:
                continue

            seen.add(key)
            merged.append(source)

    return merged


def _merged_source_type(sources: list[dict]) -> str:
    source_types = {
        source.get("source_type")
        for source in sources
        if source.get("source_type")
    }

    if len(source_types) > 1:
        return "mixed"

    if source_types:
        return sorted(source_types)[0]

    return "unknown"


def _serialize_evaluation(evaluation) -> dict:
    if hasattr(evaluation, "__dataclass_fields__"):
        item = asdict(evaluation)
    else:
        item = dict(evaluation)

    now = datetime.now().isoformat(
        timespec="seconds",
    )

    item.setdefault("status", "pending")
    item.setdefault("created_at", now)
    item["updated_at"] = now

    if item["status"] not in VALID_STATUSES:
        item["status"] = "pending"

    item["sources"] = _normalized_sources(item)
    item["source_type"] = _merged_source_type(
        item["sources"]
    )

    return item


def _candidate_confidence(item: dict) -> float:
    try:
        return float(
            item.get(
                "confidence",
                0,
            )
        )
    except (TypeError, ValueError):
        return 0.0


def _should_persist_candidate(item: dict) -> bool:
    if item.get("is_skill"):
        return True

    candidate_type = str(
        item.get("candidate_type") or ""
    ).lower()

    return not (
        candidate_type in {"context", "unknown"}
        and _candidate_confidence(item) <= 0
    )


def add_review_candidates(evaluations) -> list[dict]:
    queue = load_review_queue()
    existing = {
        _queue_key(item): item
        for item in queue
    }

    for evaluation in evaluations:
        item = _serialize_evaluation(
            evaluation
        )

        if not _should_persist_candidate(item):
            continue

        key = _queue_key(item)

        if key in existing:
            previous = existing[key]
            document_source = _merge_sources(
                previous.get("document_source", ""),
                item.get("document_source", ""),
            )
            sources = _merge_source_lists(
                previous,
                item,
            )

            if item.get("confidence", 0) >= previous.get(
                "confidence",
                0,
            ):
                status = previous.get(
                    "status",
                    "pending",
                )
                previous.update(item)
                previous["status"] = status

            previous["document_source"] = document_source
            previous["sources"] = sources
            previous["source_type"] = _merged_source_type(
                sources
            )
            if (
                previous.get("candidate_domain") in {None, "", "unknown"}
                and item.get("candidate_domain")
                and item.get("candidate_domain") != "unknown"
            ):
                previous["candidate_domain"] = item.get(
                    "candidate_domain"
                )
            previous.setdefault(
                "status",
                "pending",
            )
        else:
            queue.append(item)
            existing[key] = item

    save_review_queue(queue)

    return queue


def update_review_status(
    item_key: str,
    status: str,
    canonical_name: str | None = None,
    candidate_type: str | None = None,
    aliases: list[str] | None = None,
    existing_skill_id: int | None = None,
) -> list[dict]:
    if status not in VALID_STATUSES:
        raise ValueError(
            f"Unknown review status: {status}"
        )

    queue = load_review_queue()
    now = datetime.now().isoformat(
        timespec="seconds",
    )
    registry_result = None

    try:
        for item in queue:
            if review_item_key(item) == item_key:
                if status in {"approved", "rejected"}:
                    from jobagent.services.skill_registry_service import (
                        persist_reviewed_skill,
                    )

                    result = persist_reviewed_skill(
                        item,
                        status=status,
                        canonical_name=canonical_name,
                        skill_type=candidate_type,
                        aliases=aliases,
                        existing_skill_id=existing_skill_id,
                    )
                    registry_result = result

                    if result.conflict:
                        item["status"] = "pending"
                        item["registry_conflict"] = result.conflict.model_dump()
                        item["updated_at"] = now
                        continue

                    item["registry_conflict"] = None
                    item["registry_action"] = result.action
                    if result.entry:
                        item["registry_skill_id"] = result.entry.id
                        item["canonical_name"] = result.entry.canonical_name
                        item["candidate_type"] = result.entry.type
                    elif status == "rejected":
                        item.pop(
                            "registry_skill_id",
                            None,
                        )

                item["status"] = status
                item["updated_at"] = now

        save_review_queue(queue)
    except Exception:
        if registry_result:
            from jobagent.services.skill_registry_service import (
                rollback_skill_registry_write,
            )

            rollback_skill_registry_write(
                registry_result
            )
        raise

    return queue
