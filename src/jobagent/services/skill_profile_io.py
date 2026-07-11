import csv
import io

from jobagent.models.tag_labels import label_tag


PREFERENCE_KEY_TO_CSV_KEY = {
    "salary_minimum": "salary_minimum",
    "salary_target": "salary_target",
    "salary_dream": "salary_dream",
    "work_model_preferred": "work_model_preferred",
    "work_model_acceptable": "work_model_acceptable",
    "hard_exclusion_industries": "exclusion_industries",
    "hard_exclusion_employment_models": "exclusion_employment_models",
    "hard_exclusion_requirements": "exclusion_requirements",
}

CSV_KEY_TO_PREFERENCE_KEY = {
    csv_key: preference_key
    for preference_key, csv_key in PREFERENCE_KEY_TO_CSV_KEY.items()
}

LIST_PREFERENCE_KEYS = {
    "work_model_preferred",
    "work_model_acceptable",
    "hard_exclusion_industries",
    "hard_exclusion_employment_models",
    "hard_exclusion_requirements",
}

INT_PREFERENCE_KEYS = {
    "salary_minimum",
    "salary_target",
    "salary_dream",
}


def _csv_list(values) -> str:
    return ";".join(
        str(value).strip()
        for value in values or []
        if str(value).strip()
    )


def _parse_csv_list(value: str) -> list[str]:
    return [
        item.strip()
        for item in str(value or "").split(";")
        if item.strip()
    ]


def skill_candidates_to_csv(skills, preferences: dict | None = None) -> str:
    output = io.StringIO()

    writer = csv.DictWriter(
        output,
        fieldnames=[
            "type",
            "key",
            "value",
            "Skill-Name",
            "Kategorie",
            "Confidence",
            "Weight",
            "Enabled",
            "Source",
            "Provider",
            "Domain",
            "tag",
            "label",
        ],
    )

    writer.writeheader()

    for skill in skills:
        writer.writerow(
            {
                "type": "skill",
                "Skill-Name": skill.name,
                "Kategorie": skill.category,
                "Confidence": skill.confidence,
                "Weight": skill.weight,
                "Enabled": skill.enabled,
                "Source": skill.source,
                "Provider": skill.provider,
                "Domain": getattr(
                    skill,
                    "candidate_domain",
                    "",
                ) or "",
                "tag": skill.name,
                "label": label_tag(skill.name),
            }
        )

    if preferences:
        for preference_key, csv_key in PREFERENCE_KEY_TO_CSV_KEY.items():
            value = preferences.get(
                preference_key
            )

            if preference_key in LIST_PREFERENCE_KEYS:
                value = _csv_list(
                    value
                )
            elif value is None:
                value = ""

            writer.writerow(
                {
                    "type": "preference",
                    "key": csv_key,
                    "value": value,
                }
            )

    return output.getvalue()

from jobagent.models.skill_candidate import SkillCandidate


def _as_bool(value, default: bool = True) -> bool:
    if value is None or value == "":
        return default

    return str(value).strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "ja",
    }


def _as_int(value, default: int) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _as_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def skill_candidates_from_csv(csv_content: str) -> list[SkillCandidate]:
    input_file = io.StringIO(
        csv_content.lstrip("\ufeff")
    )

    reader = csv.DictReader(input_file)

    skills = []

    for row in reader:
        row = {
            (key or "").strip().lower(): value
            for key, value in row.items()
        }

        if (row.get("type") or "").strip().lower() == "preference":
            continue

        skill_name = (
            row.get("skill-name")
            or row.get("skill_name")
            or row.get("skill name")
            or row.get("tag")
            or row.get("skill")
            or row.get("name")
            or ""
        ).strip()

        if not skill_name:
            continue

        enabled = _as_bool(
            row.get("enabled"),
            True,
        )

        weight = _as_int(
            row.get("weight"),
            5,
        )

        confidence = _as_float(
            row.get("confidence"),
            1.0,
        )

        skills.append(
            SkillCandidate(
                name=skill_name,
                category=(
                    row.get("kategorie")
                    or row.get("category")
                    or skill_name
                ),
                confidence=confidence,
                weight=weight,
                enabled=enabled,
                source=row.get("source", ""),
                provider=row.get("provider") or "csv",
                candidate_domain=(
                    row.get("domain")
                    or row.get("candidate_domain")
                    or None
                ),
            )
        )

    return skills


def profile_preferences_from_csv(csv_content: str) -> dict:
    input_file = io.StringIO(
        csv_content.lstrip("\ufeff")
    )

    reader = csv.DictReader(input_file)
    preferences = {}

    for row in reader:
        normalized_row = {
            (key or "").strip().lower(): value
            for key, value in row.items()
        }

        if (
            normalized_row.get("type", "").strip().lower()
            != "preference"
        ):
            continue

        csv_key = (
            normalized_row.get("key")
            or normalized_row.get("preference")
            or ""
        ).strip()
        preference_key = CSV_KEY_TO_PREFERENCE_KEY.get(
            csv_key
        )

        if not preference_key:
            continue

        value = normalized_row.get("value", "")

        if preference_key in INT_PREFERENCE_KEYS:
            preferences[preference_key] = _as_int(
                value,
                0,
            )
        elif preference_key in LIST_PREFERENCE_KEYS:
            preferences[preference_key] = _parse_csv_list(
                value
            )
        else:
            preferences[preference_key] = value

    return preferences
