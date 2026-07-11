def compare_tags(
    profile_tags: set[str],
    job_tags: list[str],
) -> tuple[list[str], list[str]]:
    matches = []
    missing = []

    for tag in job_tags:
        if tag in profile_tags:
            matches.append(tag)
        else:
            missing.append(tag)

    return matches, missing