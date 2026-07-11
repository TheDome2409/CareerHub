import hashlib
import json
from pathlib import Path

from jobagent.models.recommendation_snapshot import (
    RecommendationSnapshot,
    ScoreComponents,
)
from jobagent.repositories import JsonRecommendationSnapshotRepository


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RECOMMENDATION_SNAPSHOTS_FILE = (
    PROJECT_ROOT / "data" / "recommendation_snapshots.json"
)


def _repository(
    path: str | Path = RECOMMENDATION_SNAPSHOTS_FILE,
) -> JsonRecommendationSnapshotRepository:
    return JsonRecommendationSnapshotRepository(
        path
    )


def _get_value(source, name: str, default=None):
    if isinstance(source, dict):
        return source.get(name, default)

    return getattr(source, name, default)


def _job_key(job) -> str:
    return "|".join(
        [
            str(getattr(job, "title", "") or ""),
            str(getattr(job, "company", "") or ""),
            str(getattr(job, "url", "") or ""),
            str(getattr(job, "source_name", "") or ""),
        ]
    )


def stable_recommendation_id(
    profile_fingerprint: str,
    job,
) -> str:
    payload = {
        "profile_fingerprint": profile_fingerprint,
        "job": _job_key(job),
        "query_source": getattr(job, "query_source", None) or "",
    }

    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _job_id(job) -> str:
    payload = "|".join(
        [
            str(getattr(job, "title", "") or ""),
            str(getattr(job, "company", "") or ""),
            str(getattr(job, "url", "") or ""),
            str(getattr(job, "source_name", "") or ""),
            str(getattr(job, "query_source", "") or ""),
        ]
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def _salary_info(job) -> dict[str, int] | None:
    salary_min = getattr(job, "salary_min", None)
    salary_max = getattr(job, "salary_max", None)

    if salary_min is None and salary_max is None:
        return None

    salary = {}

    if salary_min is not None:
        salary["salary_min"] = salary_min

    if salary_max is not None:
        salary["salary_max"] = salary_max

    return salary


def build_recommendation_snapshot(
    profile_fingerprint: str,
    job,
    score_result,
    query_source: str | None = None,
    recommendation_id: str | None = None,
    qualification_status: str | None = None,
) -> RecommendationSnapshot:
    score_components = ScoreComponents(
        role_score=int(_get_value(score_result, "role_score", 0) or 0),
        work_model_score=int(
            _get_value(score_result, "work_model_score", 0) or 0
        ),
        salary_score=int(
            _get_value(score_result, "salary_score", 0) or 0
        ),
        career_score=int(
            _get_value(score_result, "career_score", 0) or 0
        ),
        employer_score=int(
            _get_value(score_result, "employer_score", 0) or 0
        ),
        skill_score=int(
            _get_value(score_result, "skill_score", 0) or 0
        ),
        competency_score=int(
            _get_value(score_result, "competency_score", 0) or 0
        ),
        role_mismatch_penalty=int(
            _get_value(score_result, "role_mismatch_penalty", 0) or 0
        ),
    )

    return RecommendationSnapshot(
        recommendation_id=(
            recommendation_id
            or stable_recommendation_id(
                profile_fingerprint,
                job,
            )
        ),
        profile_fingerprint=profile_fingerprint,
        job_id=_job_id(job),
        job_title=getattr(job, "title", ""),
        company=getattr(job, "company", None),
        query_source=query_source or getattr(job, "query_source", None),
        total_score=int(
            _get_value(
                score_result,
                "total_score",
                _get_value(score_result, "score", 0),
            )
            or 0
        ),
        score_components=score_components,
        skill_match_ratio=float(
            _get_value(score_result, "skill_match_ratio", 0.0) or 0.0
        ),
        matched_skills=sorted(
            _get_value(score_result, "matched_skills", []) or []
        ),
        missing_skills=sorted(
            _get_value(score_result, "missing_skills", []) or []
        ),
        salary_info=_salary_info(job),
        work_model=getattr(job, "work_model", None),
        qualification_status=qualification_status,
    )


def serialize_snapshot(
    snapshot: RecommendationSnapshot,
) -> dict:
    return snapshot.model_dump(
        mode="json"
    )


def snapshot_to_json(
    snapshot: RecommendationSnapshot,
) -> str:
    return json.dumps(
        serialize_snapshot(snapshot),
        ensure_ascii=False,
        indent=2,
    )


def _deduplicate_snapshots(snapshots: list[dict]) -> list[dict]:
    deduplicated = {}

    for snapshot in snapshots:
        recommendation_id = str(
            snapshot.get("recommendation_id", "") or ""
        )

        if not recommendation_id:
            continue

        deduplicated.setdefault(
            recommendation_id,
            snapshot,
        )

    return list(
        deduplicated.values()
    )


def append_snapshot(
    path: str | Path,
    snapshot: RecommendationSnapshot,
) -> None:
    _repository(
        path
    ).append_snapshot(
        snapshot
    )


def save_snapshot_once(
    snapshot: RecommendationSnapshot,
    path: str | Path = RECOMMENDATION_SNAPSHOTS_FILE,
) -> None:
    append_snapshot(
        path,
        snapshot,
    )


def load_snapshots(
    path: str | Path = RECOMMENDATION_SNAPSHOTS_FILE,
) -> list[RecommendationSnapshot]:
    return _repository(
        path
    ).load_snapshots()


def save_snapshots(
    snapshots: list[RecommendationSnapshot],
    path: str | Path = RECOMMENDATION_SNAPSHOTS_FILE,
) -> None:
    _repository(
        path
    ).save_snapshots(
        snapshots
    )
