from jobagent.models.skill_candidate import (
    SkillCandidate,
)


def build_skill_candidates(
    detected_tags: dict[str, set[str]],
) -> list[SkillCandidate]:

    candidates = []

    for tag, keywords in detected_tags.items():
        candidates.append(
            SkillCandidate(
                name=tag,
                category=tag,
                confidence=1.0,
                weight=5,
                enabled=True,
                source=", ".join(
                    sorted(keywords)
                ),
            )
        )

    return candidates