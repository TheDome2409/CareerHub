from pathlib import Path

import yaml


def _taxonomy_file() -> Path:
    return (
        Path(__file__)
        .resolve()
        .parents[3]
        / "config"
        / "skill_taxonomy.yaml"
    )


def _load_yaml_taxonomy() -> dict:
    taxonomy_file = _taxonomy_file()

    with open(
        taxonomy_file,
        "r",
        encoding="utf-8",
    ) as f:
        return yaml.safe_load(f) or {}


def _taxonomy_from_registry() -> dict:
    from jobagent.services.skill_registry_service import (
        list_skills,
        migrate_taxonomy_to_skill_registry,
    )

    migrate_taxonomy_to_skill_registry()
    taxonomy = {}

    for skill in list_skills():
        taxonomy[skill.canonical_name] = {
            "label": skill.display_name,
            "keywords": [
                alias
                for alias in skill.aliases
                if alias
            ],
            "source": "skill_registry",
            "type": skill.type,
        }

    seed_taxonomy = _load_yaml_taxonomy()
    for canonical_name, data in seed_taxonomy.items():
        if canonical_name not in taxonomy:
            continue
        keywords = list(
            taxonomy[canonical_name].get("keywords") or []
        )
        for keyword in (data or {}).get("keywords", []) or []:
            if keyword and keyword not in keywords:
                keywords.append(keyword)
        taxonomy[canonical_name]["keywords"] = keywords

    return taxonomy


def load_taxonomy() -> dict:
    try:
        taxonomy = _taxonomy_from_registry()
        if taxonomy:
            return taxonomy
    except Exception:
        pass

    taxonomy = _load_yaml_taxonomy()

    try:
        from jobagent.services.skill_registry_service import (
            list_skills,
        )

        for skill in list_skills():
            taxonomy.setdefault(
                skill.canonical_name,
                {
                    "label": skill.display_name,
                    "keywords": [],
                },
            )
            entry = taxonomy[skill.canonical_name]
            keywords = list(
                entry.get("keywords") or []
            )
            for alias in skill.aliases:
                if alias and alias not in keywords:
                    keywords.append(alias)
            if skill.display_name and skill.display_name not in keywords:
                keywords.append(skill.display_name)
            entry["keywords"] = keywords
            entry.setdefault(
                "label",
                skill.display_name,
            )
    except Exception:
        pass

    return taxonomy
