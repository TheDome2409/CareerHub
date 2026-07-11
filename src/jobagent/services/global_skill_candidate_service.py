from datetime import datetime
from pathlib import Path

from jobagent.models.global_skill_candidate import GlobalSkillCandidate
from jobagent.repositories import JsonGlobalSkillCandidateRepository


PROJECT_ROOT = Path(__file__).resolve().parents[3]
GLOBAL_SKILL_CANDIDATES_FILE = (
    PROJECT_ROOT / "data" / "global_skill_candidates.json"
)
TAXONOMY_CANDIDATE_ACCEPTED_THRESHOLD = 5
TAXONOMY_CANDIDATE_CONFIDENCE_THRESHOLD = 0.75
MAX_EXAMPLE_REASONS = 5


def _repository(
    path: str | Path = GLOBAL_SKILL_CANDIDATES_FILE,
) -> JsonGlobalSkillCandidateRepository:
    return JsonGlobalSkillCandidateRepository(
        path
    )


def _normalize_key(value: str) -> str:
    return str(value or "").strip().lower()


def _canonical_name(item: dict) -> str:
    return str(
        item.get("canonical_name")
        or item.get("suggested_tag")
        or item.get("name")
        or ""
    ).strip()


def _parse_datetime(value) -> datetime | None:
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
    except ValueError:
        return None


def _append_unique(values: list[str], value: str | None) -> None:
    value = str(value or "").strip()

    if value and value not in values:
        values.append(value)


def _source_types(item: dict) -> list[str]:
    source_types = []

    _append_unique(
        source_types,
        item.get("source_type"),
    )

    sources = item.get("sources")

    if isinstance(sources, list):
        for source in sources:
            if isinstance(source, dict):
                _append_unique(
                    source_types,
                    source.get("source_type"),
                )

    return source_types


def _status_counts(status: str) -> tuple[int, int]:
    status = str(status or "pending").lower()

    if status in {"approved", "accepted"}:
        return 1, 0

    if status == "rejected":
        return 0, 1

    return 0, 0


def _number(item: dict, key: str) -> float:
    try:
        return float(
            item.get(key, 0) or 0
        )
    except (TypeError, ValueError):
        return 0.0


def _taxonomy_status(candidate: GlobalSkillCandidate) -> str:
    categories = {
        category.lower()
        for category in candidate.categories
    }

    if (
        candidate.accepted_count >= TAXONOMY_CANDIDATE_ACCEPTED_THRESHOLD
        and candidate.confidence_avg
        >= TAXONOMY_CANDIDATE_CONFIDENCE_THRESHOLD
        and "other" not in categories
    ):
        return "taxonomy_candidate"

    return "observed"


def update_statistics(
    candidate: GlobalSkillCandidate,
    confidence_total: float,
    weight_total: float,
) -> GlobalSkillCandidate:
    if candidate.seen_count <= 0:
        candidate.confidence_avg = 0.0
        candidate.weight_avg = 0.0
    else:
        candidate.confidence_avg = round(
            confidence_total / candidate.seen_count,
            4,
        )
        candidate.weight_avg = round(
            weight_total / candidate.seen_count,
            4,
        )

    candidate.status = _taxonomy_status(
        candidate
    )

    return candidate


def merge_candidate(
    candidate: GlobalSkillCandidate | None,
    item: dict,
    totals: dict[str, dict[str, float]],
) -> GlobalSkillCandidate:
    canonical_name = _canonical_name(item)

    if not canonical_name:
        raise ValueError(
            "Review queue item has no candidate name"
        )

    if candidate is None:
        candidate = GlobalSkillCandidate(
            canonical_name=canonical_name
        )

    key = _normalize_key(
        candidate.canonical_name
    )
    totals.setdefault(
        key,
        {
            "confidence": 0.0,
            "weight": 0.0,
        },
    )

    for alias in [
        item.get("name"),
        item.get("suggested_tag"),
        item.get("canonical_name"),
    ]:
        _append_unique(
            candidate.aliases,
            alias,
        )

    _append_unique(
        candidate.categories,
        item.get("category"),
    )
    _append_unique(
        candidate.candidate_domains,
        item.get("candidate_domain"),
    )

    for source_type in _source_types(item):
        _append_unique(
            candidate.source_types,
            source_type,
        )

    reason = str(
        item.get("reason") or ""
    ).strip()

    if (
        reason
        and reason not in candidate.example_reasons
        and len(candidate.example_reasons) < MAX_EXAMPLE_REASONS
    ):
        candidate.example_reasons.append(
            reason
        )

    created_at = _parse_datetime(
        item.get("created_at")
    )
    updated_at = _parse_datetime(
        item.get("updated_at")
    )
    seen_at = updated_at or created_at

    if seen_at:
        if candidate.first_seen is None or seen_at < candidate.first_seen:
            candidate.first_seen = seen_at

        if candidate.last_seen is None or seen_at > candidate.last_seen:
            candidate.last_seen = seen_at

    accepted, rejected = _status_counts(
        item.get("status")
    )

    candidate.seen_count += 1
    candidate.accepted_count += accepted
    candidate.rejected_count += rejected
    totals[key]["confidence"] += _number(
        item,
        "confidence",
    )
    totals[key]["weight"] += _number(
        item,
        "weight",
    )

    return update_statistics(
        candidate,
        totals[key]["confidence"],
        totals[key]["weight"],
    )


def build_global_candidates(
    review_queue: list[dict],
) -> list[GlobalSkillCandidate]:
    candidates = {}
    totals = {}

    for item in review_queue:
        canonical_name = _canonical_name(item)

        if not canonical_name:
            continue

        key = _normalize_key(
            canonical_name
        )
        candidates[key] = merge_candidate(
            candidates.get(key),
            item,
            totals,
        )

    return sorted(
        candidates.values(),
        key=lambda candidate: candidate.canonical_name.lower(),
    )


def load_candidates(
    path: str | Path = GLOBAL_SKILL_CANDIDATES_FILE,
) -> list[GlobalSkillCandidate]:
    return _repository(
        path
    ).load_candidates()


def save_candidates(
    candidates: list[GlobalSkillCandidate],
    path: str | Path = GLOBAL_SKILL_CANDIDATES_FILE,
) -> None:
    _repository(
        path
    ).save_candidates(
        candidates
    )
