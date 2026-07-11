from jobagent.services.keyword_detector import (
    detect_keyword_matches,
)
from jobagent.services.skill_alias_service import (
    canonicalize_skill,
    canonicalize_skills,
)
from jobagent.services.skill_candidate_domain_service import (
    normalize_domain_text,
)


JOB_SKILL_FRAGMENT_TERMS = {
    "as code zero",
    "landing zone platform",
}


def _is_job_skill_fragment(skill: str) -> bool:
    normalized = normalize_domain_text(skill)

    return normalized in JOB_SKILL_FRAGMENT_TERMS


def extract_job_required_skills(
    job_description: str,
) -> set[str]:
    from jobagent.services.unknown_skill_service import (
        detect_unknown_skill_candidates,
    )

    matches = detect_keyword_matches(
        job_description or ""
    )

    skills = set(
        matches.keys()
    )

    for skill in detect_unknown_skill_candidates(
        job_description or ""
    ):
        if not _is_job_skill_fragment(skill):
            skills.add(skill)

    return canonicalize_skills(
        skills
    )


def _normalized_tag_map(tags: set[str]) -> dict[str, str]:
    normalized = {}

    for tag in tags:
        value = str(tag).strip()

        if not value:
            continue

        normalized.setdefault(
            canonicalize_skill(value),
            canonicalize_skill(value),
        )

    return normalized


def compare_profile_to_job(
    profile_tags: set[str],
    job_tags: set[str],
) -> tuple[set[str], set[str]]:
    profile_map = _normalized_tag_map(
        profile_tags
    )
    job_map = _normalized_tag_map(
        job_tags
    )
    matched_keys = set(profile_map).intersection(job_map)

    for job_key in job_map:
        if job_key in matched_keys:
            continue

        if len(job_key) < 4:
            continue

        if any(
            job_key in profile_key
            for profile_key in profile_map
        ):
            matched_keys.add(job_key)

    matched_tags = {
        job_map[key]
        for key in matched_keys
    }

    missing_tags = {
        original
        for key, original in job_map.items()
        if key not in matched_keys
    }

    return matched_tags, missing_tags


def calculate_skill_match(
    profile_tags: set[str],
    job_description: str,
) -> tuple[set[str], set[str], float]:
    job_tags = extract_job_required_skills(
        job_description
    )

    if not job_tags:
        return set(), set(), 0.0

    matched_tags, missing_tags = compare_profile_to_job(
        profile_tags,
        job_tags,
    )
    total_tags = len(matched_tags) + len(missing_tags)
    match_ratio = len(matched_tags) / total_tags if total_tags else 0.0

    return matched_tags, missing_tags, match_ratio
