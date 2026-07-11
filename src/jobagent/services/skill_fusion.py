from jobagent.models.skill_candidate import (
    SkillCandidate,
)


def merge_skill_candidates(
    skills: list[SkillCandidate],
) -> list[SkillCandidate]:

    merged = {}

    for skill in skills:

        if skill.name not in merged:
            merged[skill.name] = skill
            continue

        existing = merged[skill.name]

        existing.confidence = max(
            existing.confidence,
            skill.confidence,
        )

        if skill.provider not in existing.source:
            existing.source += (
                f" | {skill.provider}: {skill.source}"
            )

    return list(merged.values())