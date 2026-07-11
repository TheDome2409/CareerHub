from pathlib import Path
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from jobagent.core.config_loader import (
    load_profile,
    load_scoring,
)

from jobagent.services.job_ranker import JobRanker
from jobagent.services.competency_service import (
    compare_competencies,
    extract_job_competencies,
    extract_profile_competencies,
)
from jobagent.services.job_intelligence_service import (
    analyze_job,
)
from jobagent.services.profile_search_query_service import (
    build_search_queries,
)
from jobagent.services.qualification_service import (
    evaluate_qualification_gap,
)
from jobagent.services.scorer import JobScorer

from jobagent.sources.source_loader import load_sources
from jobagent.sources.source_factory import SourceFactory


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = PROJECT_ROOT / "config"
QUERY_SOURCE_TYPES = {
    "bundesagentur",
    "remotive",
}


def _sources_config_path() -> Path:
    active_path = CONFIG_DIR / "sources.yaml"

    if active_path.exists():
        return active_path

    return CONFIG_DIR / "sources.example.yaml"


def _resolve_project_path(path: str | None) -> str | None:
    if not path:
        return path

    candidate = Path(path)

    if candidate.is_absolute():
        return str(candidate)

    return str(PROJECT_ROOT / candidate)


def _resolve_source_paths(source_config):
    updates = {}

    if source_config.path:
        updates["path"] = _resolve_project_path(
            source_config.path
        )

    if source_config.url:
        url = source_config.url

        if "://" not in url:
            updates["url"] = _resolve_project_path(url)

    if not updates:
        return source_config

    return source_config.model_copy(update=updates)


def _normalize_text(value: str | None) -> str:
    value = (value or "").lower()
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def _canonical_url(url: str | None) -> str | None:
    if not url:
        return None

    parts = urlsplit(url)
    query = [
        (key, value)
        for key, value in parse_qsl(
            parts.query,
            keep_blank_values=True,
        )
        if not key.lower().startswith("utm_")
    ]

    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            urlencode(query),
            "",
        )
    )


def _dedupe_key(job) -> tuple[str, str]:
    canonical_url = _canonical_url(job.url)

    if canonical_url:
        return ("url", canonical_url)

    return (
        "title_company",
        "|".join(
            [
                _normalize_text(job.title),
                _normalize_text(job.company),
            ]
        ),
    )


def _deduplicate_jobs(jobs):
    unique_jobs = []
    seen = set()

    for job in jobs:
        key = _dedupe_key(job)

        if key in seen:
            continue

        seen.add(key)
        unique_jobs.append(job)

    return unique_jobs


def _source_supports_profile_queries(source_config) -> bool:
    return source_config.type in QUERY_SOURCE_TYPES


def _should_load_source(
    source_config,
    search_queries: list[str],
    profile_bound: bool,
) -> bool:
    if not profile_bound or not search_queries:
        return True

    return _source_supports_profile_queries(source_config)


def _profile_aware_source_configs(
    source_config,
    queries: list[str],
):
    if not _source_supports_profile_queries(source_config):
        return [source_config]

    if not queries:
        return [source_config]

    max_results = source_config.max_results
    per_query_max_results = None

    if max_results:
        per_query_max_results = max(
            5,
            min(
                max_results,
                -(-max_results // len(queries)),
            ),
        )

    configs = []

    for query in queries:
        updates = {
            "query": query,
        }

        if per_query_max_results:
            updates["max_results"] = per_query_max_results

        configs.append(
            source_config.model_copy(
                update=updates
            )
        )

    return configs


def _profile_with_session_skills(
    profile,
    profile_skills,
    profile_preferences=None,
):
    if profile_skills is None and not profile_preferences:
        return profile

    updates = {}

    if profile_skills is not None:
        updates["preferred_roles"] = []
        updates["skills"] = sorted(
            {
                str(skill).strip()
                for skill in profile_skills
                if str(skill).strip()
            },
            key=str.lower,
        )

    if profile_preferences:
        salary = profile.profile.salary.model_copy(
            update={
                "minimum": int(
                    profile_preferences.get("salary_minimum")
                    or profile.profile.salary.minimum
                ),
                "target": int(
                    profile_preferences.get("salary_target")
                    or profile.profile.salary.target
                ),
                "dream": int(
                    profile_preferences.get("salary_dream")
                    or profile.profile.salary.dream
                ),
            }
        )
        exclusions = profile.profile.exclusions.model_copy(
            update={
                "industries": list(
                    profile_preferences.get(
                        "hard_exclusion_industries",
                        profile.profile.exclusions.industries,
                    )
                    or []
                ),
                "employment_models": list(
                    profile_preferences.get(
                        "hard_exclusion_employment_models",
                        profile.profile.exclusions.employment_models,
                    )
                    or []
                ),
                "requirements": list(
                    profile_preferences.get(
                        "hard_exclusion_requirements",
                        profile.profile.exclusions.requirements,
                    )
                    or []
                ),
            }
        )
        updates["salary"] = salary
        updates["exclusions"] = exclusions

        work_model = profile.profile.work_model.model_copy(
            update={
                "preferred": list(
                    profile_preferences.get(
                        "work_model_preferred",
                        profile.profile.work_model.preferred,
                    )
                    or []
                ),
                "acceptable": list(
                    profile_preferences.get(
                        "work_model_acceptable",
                        profile.profile.work_model.acceptable,
                    )
                    or []
                ),
            }
        )
        updates["work_model"] = work_model

    profile_data = profile.profile.model_copy(
        update=updates
    )

    return profile.model_copy(
        update={
            "profile": profile_data,
        }
    )


def _load_runtime_profile(profile_skills=None, profile_preferences=None):
    profile_bound = profile_skills is not None
    profile = load_profile(
        CONFIG_DIR / "profile.example.yaml"
    )
    profile = _profile_with_session_skills(
        profile,
        profile_skills,
        profile_preferences,
    )

    return profile, profile_bound


def build_runtime_search_queries(
    profile_skills=None,
    profile_preferences=None,
) -> list[str]:
    profile, _profile_bound = _load_runtime_profile(
        profile_skills,
        profile_preferences,
    )

    return build_search_queries(
        profile
    )


def build_runtime_profile(
    profile_skills=None,
    profile_preferences=None,
):
    profile, _profile_bound = _load_runtime_profile(
        profile_skills,
        profile_preferences,
    )

    return profile


def load_and_rank_jobs(
    min_score: int = 20,
    profile_skills=None,
    search_queries: list[str] | None = None,
    profile_preferences=None,
):
    profile, profile_bound = _load_runtime_profile(
        profile_skills,
        profile_preferences,
    )

    scoring = load_scoring(
        CONFIG_DIR / "scoring.example.yaml"
    )

    sources_config = load_sources(
        _sources_config_path()
    )
    if search_queries is None:
        search_queries = build_search_queries(
            profile
        )

    jobs = []

    for source_config in sources_config.sources:

        if not source_config.enabled:
            continue

        if not _should_load_source(
            source_config,
            search_queries,
            profile_bound,
        ):
            continue

        for profile_source_config in _profile_aware_source_configs(
            source_config,
            search_queries,
        ):
            resolved_source_config = _resolve_source_paths(
                profile_source_config
            )

            source = SourceFactory.create(
                resolved_source_config
            )

            loaded_jobs = source.load()

            if loaded_jobs:
                for job in loaded_jobs:
                    if resolved_source_config.query:
                        job.query_source = resolved_source_config.query

                jobs.extend(
                    loaded_jobs
                )

    jobs = _deduplicate_jobs(
        jobs
    )

    scorer = JobScorer(
        profile=profile,
        scoring=scoring,
    )

    ranker = JobRanker(
        scorer
    )

    ranked_jobs = ranker.rank(
        jobs
    )

    profile_competencies = extract_profile_competencies(
        profile
    )

    for result in ranked_jobs:
        result["job_intelligence"] = analyze_job(
            result["job"]
        )
        result["qualification_result"] = evaluate_qualification_gap(
            profile,
            result["job"],
            result["job_intelligence"],
        )
        job_competencies = extract_job_competencies(
            result["job"]
        )
        competency_match = compare_competencies(
            profile_competencies,
            job_competencies,
        )
        result["competency_match"] = competency_match
        result["competency_match_ratio"] = competency_match[
            "competency_match_ratio"
        ]
        result["matched_competencies"] = competency_match[
            "matched_competencies"
        ]
        result["missing_competencies"] = competency_match[
            "missing_competencies"
        ]
        result["competency_matches"] = competency_match[
            "matches"
        ]

    ranked_jobs = [
        result
        for result in ranked_jobs
        if result["score"] > -100
        and result["score"] >= min_score
    ]

    return ranked_jobs
