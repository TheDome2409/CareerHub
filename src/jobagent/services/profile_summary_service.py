from jobagent.models.tag_labels import (
    label_tag,
)


CORE_SKILLS = {
    "digitalization",
    "automation",
    "architecture",
    "cloud",
    "security",
    "data",
    "innovation",
}

MANAGEMENT_SKILLS = {
    "leadership",
    "stakeholder_management",
    "project_responsibility",
    "consulting",
    "change_management",
    "vendor_management",
    "budget_responsibility",
    "strategic_role",
    "governance",
    "product",
    "platform",
}

SOCIAL_SKILLS = {
    "social_engagement",
}


def _labels_for(
    profile_tags: list[str],
    allowed_tags: set[str],
) -> list[str]:
    return [
        label_tag(tag)
        for tag in sorted(profile_tags)
        if tag in allowed_tags
    ]


def _add_section(
    lines: list[str],
    title: str,
    values: list[str],
) -> None:
    if not values:
        return

    lines.append(title)
    lines.append(", ".join(values))
    lines.append("")


def generate_profile_summary(
    profile_tags: list[str],
) -> str:
    core_skills = _labels_for(
        profile_tags,
        CORE_SKILLS,
    )

    management_skills = _labels_for(
        profile_tags,
        MANAGEMENT_SKILLS,
    )

    social_skills = _labels_for(
        profile_tags,
        SOCIAL_SKILLS,
    )

    lines = []

    _add_section(
        lines,
        "Kernkompetenzen:",
        core_skills,
    )

    _add_section(
        lines,
        "Management & Organisation:",
        management_skills,
    )

    _add_section(
        lines,
        "Zusätzliche Stärken:",
        social_skills,
    )

    if not lines:
        return (
            "Es wurden noch keine belastbaren "
            "Profilinformationen erkannt."
        )

    return "\n".join(lines).strip()