from jobagent.services import companyhub_db_service
from jobagent.services.job_skill_service import compare_profile_to_job
from jobagent.services.skill_alias_service import (
    are_same_skill,
    canonicalize_skill,
)
from jobagent.services.skill_registry_service import save_skill


def test_artificial_intelligence_aliases_match():
    matched, missing = compare_profile_to_job(
        {"KI", "LLM"},
        {"AI", "Artificial Intelligence"},
    )

    assert matched == {"artificial_intelligence"}
    assert "AI" not in missing
    assert missing == set()


def test_project_management_aliases_match():
    matched, missing = compare_profile_to_job(
        {"Projektleitung"},
        {"Project Management"},
    )

    assert matched == {"project_management"}
    assert missing == set()


def test_documentation_aliases_match():
    matched, missing = compare_profile_to_job(
        {"Pflegedokumentation"},
        {"Documentation"},
    )

    assert matched == {"documentation"}
    assert missing == set()


def test_canonicalize_skill_helpers():
    assert canonicalize_skill("Generative AI") == "artificial_intelligence"
    assert are_same_skill("Veränderungsmanagement", "change management")


def test_registry_alias_has_priority_over_static_yaml_alias(tmp_path, monkeypatch):
    db_path = tmp_path / "companyhub.db"
    monkeypatch.setattr(
        companyhub_db_service,
        "DEFAULT_COMPANYHUB_DB_PATH",
        db_path,
    )
    save_skill(
        "AI Strategy",
        aliases=[
            "Generative AI",
        ],
        db_path=db_path,
    )

    assert canonicalize_skill(
        "Generative AI"
    ) == "AI Strategy"
