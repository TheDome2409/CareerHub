from jobagent.repositories import YamlTaxonomyRepository
from jobagent.services.skill_candidate_domain_service import (
    normalize_domain_text,
)


SKILL_ALIAS_GROUPS = YamlTaxonomyRepository().load_aliases()


def normalize_skill_key(value: str) -> str:
    return normalize_domain_text(
        value
    ).replace(
        " ",
        "_",
    )


def _build_alias_map() -> dict[str, str]:
    aliases = {}

    for canonical, values in SKILL_ALIAS_GROUPS.items():
        aliases[normalize_skill_key(canonical)] = canonical

        for value in values:
            aliases[normalize_skill_key(value)] = canonical

    return aliases


SKILL_ALIAS_MAP = _build_alias_map()


def canonicalize_skill(value: str) -> str:
    normalized = normalize_skill_key(
        value
    )

    try:
        from jobagent.services.skill_registry_service import (
            normalize_skill_registry_key,
            registry_alias_map,
        )

        registry_aliases = registry_alias_map()
        registry_match = registry_aliases.get(
            normalized,
        ) or registry_aliases.get(
            normalize_skill_registry_key(value),
        )
        if registry_match:
            return registry_match
    except Exception:
        pass

    static_match = SKILL_ALIAS_MAP.get(
        normalized,
        normalized,
    )

    if static_match != normalized:
        return static_match

    return normalized


def canonicalize_skills(values: list[str] | set[str]) -> set[str]:
    return {
        canonicalize_skill(value)
        for value in values or []
        if str(value).strip()
    }


def are_same_skill(a: str, b: str) -> bool:
    return canonicalize_skill(
        a
    ) == canonicalize_skill(
        b
    )
