import pytest

from jobagent.services import skill_registry_service
from jobagent.services import companyhub_db_service
from jobagent.services.job_skill_service import compare_profile_to_job
from jobagent.services.skill_alias_service import canonicalize_skill
from jobagent.services.skill_registry_service import (
    find_skill,
    list_skills,
    migrate_taxonomy_to_skill_registry,
    persist_reviewed_skill,
    registry_alias_map,
    save_skill,
)


def test_new_skill_is_persisted(tmp_path):
    db_path = tmp_path / "skills.db"

    result = save_skill(
        "Azure Landing Zone",
        aliases=[
            "Azure Landing Zones",
        ],
        created_by="test",
        source="unit_test",
        db_path=db_path,
    )

    assert result.action == "created"
    assert result.entry.id is not None
    assert result.entry.canonical_name == "Azure Landing Zone"
    assert "Azure Landing Zones" in result.entry.aliases


def test_alias_merge_prevents_duplicate_inserts(tmp_path):
    db_path = tmp_path / "skills.db"

    first = save_skill(
        "Azure Landing Zone",
        aliases=[
            "Azure Landing Zones",
        ],
        db_path=db_path,
    )
    second = save_skill(
        "Azure-Landing-Zone",
        aliases=[
            "azure landingzone",
        ],
        db_path=db_path,
    )

    skills = list_skills(
        db_path=db_path,
    )

    assert first.entry.id == second.entry.id
    assert second.action == "merged"
    assert len(skills) == 1
    assert find_skill(
        "azure landingzone",
        db_path=db_path,
    ).id == first.entry.id


def test_same_name_with_different_type_creates_review_conflict(tmp_path):
    db_path = tmp_path / "skills.db"
    save_skill(
        "Azure Landing Zone",
        skill_type="skill",
        db_path=db_path,
    )

    result = save_skill(
        "Azure Landing Zone",
        skill_type="certification",
        db_path=db_path,
    )

    assert result.action == "conflict"
    assert result.conflict.existing_type == "skill"
    assert list_skills(
        status=None,
        db_path=db_path,
    )[0].type == "skill"


def test_rejected_candidate_is_not_persisted_in_registry(tmp_path):
    db_path = tmp_path / "skills.db"

    result = persist_reviewed_skill(
        {
            "name": "Generic Noise",
            "canonical_name": "Generic Noise",
            "candidate_type": "skill",
        },
        status="rejected",
        db_path=db_path,
    )

    assert result.action == "rejected"
    assert result.entry is None
    assert list_skills(
        db_path=db_path,
    ) == []
    assert list_skills(
        status=None,
        db_path=db_path,
    ) == []


def test_review_approval_persists_skill(tmp_path):
    db_path = tmp_path / "skills.db"

    result = persist_reviewed_skill(
        {
            "name": "Azure Landing Zones",
            "canonical_name": "Azure Landing Zone",
            "suggested_tag": "azure_landing_zone",
            "candidate_type": "skill",
        },
        status="approved",
        db_path=db_path,
    )

    assert result.action == "created"
    assert find_skill(
        "Azure Landing Zones",
        db_path=db_path,
    ).canonical_name == "Azure Landing Zone"


def test_matching_uses_new_registry_skill_without_restart(tmp_path, monkeypatch):
    db_path = tmp_path / "skills.db"
    monkeypatch.setattr(
        companyhub_db_service,
        "DEFAULT_COMPANYHUB_DB_PATH",
        db_path,
    )

    save_skill(
        "Azure Landing Zone",
        aliases=[
            "Azure Landing Zones",
            "azure landingzone",
        ],
        db_path=db_path,
    )

    assert canonicalize_skill(
        "Azure-Landing-Zones"
    ) == "Azure Landing Zone"

    matched, missing = compare_profile_to_job(
        {
            "Azure Landing Zone",
        },
        {
            "azure landingzone",
        },
    )

    assert matched == {
        "Azure Landing Zone",
    }
    assert missing == set()


def test_registry_alias_read_does_not_create_database(tmp_path, monkeypatch):
    db_path = tmp_path / "missing_companyhub.db"
    monkeypatch.setattr(
        companyhub_db_service,
        "DEFAULT_COMPANYHUB_DB_PATH",
        db_path,
    )

    assert registry_alias_map() == {}
    assert not db_path.exists()


def test_taxonomy_migration_is_idempotent(tmp_path):
    db_path = tmp_path / "skills.db"

    first = migrate_taxonomy_to_skill_registry(
        db_path=db_path,
    )
    second = migrate_taxonomy_to_skill_registry(
        db_path=db_path,
    )

    assert first["created"] > 0
    assert second["created"] == 0
    assert second["merged"] >= first["created"]


@pytest.mark.parametrize("status", ["active", "inactive"])
def test_seed_refresh_preserves_human_review_provenance(tmp_path, monkeypatch, status):
    db_path = tmp_path / "skills.db"
    seed = tmp_path / "taxonomy.yaml"
    seed.write_text("seed_skill:\n  label: Seed Skill\n", encoding="utf-8")
    monkeypatch.setattr(skill_registry_service, "SKILL_TAXONOMY_FILE", seed)

    class SeedAliases:
        def load_aliases(self):
            return {"seed_skill": ["Human Alias", "New Seed Alias"]}

    monkeypatch.setattr(skill_registry_service, "YamlTaxonomyRepository", SeedAliases)
    migrate_taxonomy_to_skill_registry(db_path=db_path)
    reviewed = save_skill(
        "seed_skill", display_name="Reviewed Skill", description="Human description",
        aliases=["Human Alias"], created_by="human_review", source="review_queue",
        status=status, db_path=db_path,
    ).entry
    for _ in range(2):
        migrate_taxonomy_to_skill_registry(db_path=db_path)
    refreshed = find_skill("Human Alias", db_path=db_path)
    assert refreshed.id == reviewed.id
    assert refreshed.source == "review_queue"
    assert refreshed.created_by == reviewed.created_by
    assert refreshed.status == status
    assert refreshed.display_name == "Reviewed Skill"
    assert refreshed.description == "Human description"
    assert refreshed.updated_at == reviewed.updated_at
    assert "New Seed Alias" in refreshed.aliases


def test_seed_import_preserves_runtime_entry_and_human_alias_ownership(tmp_path, monkeypatch):
    db_path = tmp_path / "skills.db"
    runtime = save_skill(
        "Human Concept", aliases=["Shared Alias"], source="manual_registry",
        created_by="human_review", status="inactive", db_path=db_path,
    ).entry
    seed = tmp_path / "taxonomy.yaml"
    seed.write_text("seed_skill:\n  label: Shared Alias\n", encoding="utf-8")
    monkeypatch.setattr(skill_registry_service, "SKILL_TAXONOMY_FILE", seed)

    class SeedAliases:
        def load_aliases(self):
            return {"Another Concept": ["Shared Alias"]}

    monkeypatch.setattr(skill_registry_service, "YamlTaxonomyRepository", SeedAliases)
    migrate_taxonomy_to_skill_registry(db_path=db_path)
    preserved = find_skill("Shared Alias", db_path=db_path)
    assert preserved.id == runtime.id
    assert preserved.source == "manual_registry"
    assert preserved.status == "inactive"
    assert preserved.display_name == "Human Concept"


def test_seed_only_entry_can_still_receive_seed_updates(tmp_path):
    db_path = tmp_path / "skills.db"
    first = save_skill("seed", created_by="migration", source="seed.yaml", db_path=db_path)
    updated = save_skill(
        "seed", display_name="Updated seed", aliases=["New alias"],
        created_by="migration", source="seed.yaml", db_path=db_path,
    )
    assert updated.entry.id == first.entry.id
    assert updated.entry.display_name == "Updated seed"
    assert "New alias" in updated.entry.aliases


def test_taxonomy_migration_handles_missing_seed_file(tmp_path, monkeypatch):
    db_path = tmp_path / "skills.db"
    monkeypatch.setattr(
        skill_registry_service,
        "SKILL_TAXONOMY_FILE",
        tmp_path / "missing.yaml",
    )

    class EmptyRepository:
        def load_aliases(self):
            return {}

    monkeypatch.setattr(
        skill_registry_service,
        "YamlTaxonomyRepository",
        EmptyRepository,
    )

    result = migrate_taxonomy_to_skill_registry(
        db_path=db_path,
    )

    assert result["created"] == 0
    assert list_skills(
        status=None,
        db_path=db_path,
    ) == []


def test_taxonomy_migration_handles_invalid_seed_file(tmp_path, monkeypatch):
    db_path = tmp_path / "skills.db"
    broken_seed = tmp_path / "broken.yaml"
    broken_seed.write_text(
        ": [",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        skill_registry_service,
        "SKILL_TAXONOMY_FILE",
        broken_seed,
    )

    class EmptyRepository:
        def load_aliases(self):
            return {}

    monkeypatch.setattr(
        skill_registry_service,
        "YamlTaxonomyRepository",
        EmptyRepository,
    )

    result = migrate_taxonomy_to_skill_registry(
        db_path=db_path,
    )

    assert result["created"] == 0
    assert list_skills(
        status=None,
        db_path=db_path,
    ) == []


def test_taxonomy_migration_restores_snapshot_on_alias_failure(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "skills.db"
    seed = tmp_path / "taxonomy.yaml"
    seed.write_text(
        "seed_skill:\n  label: Seed Skill\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        skill_registry_service,
        "SKILL_TAXONOMY_FILE",
        seed,
    )

    class FakeRepository:
        def load_aliases(self):
            return {
                "Seed Skill": [
                    "Broken Alias",
                ],
            }

    monkeypatch.setattr(
        skill_registry_service,
        "YamlTaxonomyRepository",
        FakeRepository,
    )

    original_insert_alias = skill_registry_service._insert_alias

    def fail_for_broken_alias(connection, skill_id, alias, skill_type):
        if alias == "Broken Alias":
            raise RuntimeError(
                "forced migration alias failure"
            )
        original_insert_alias(
            connection,
            skill_id,
            alias,
            skill_type,
        )

    monkeypatch.setattr(
        skill_registry_service,
        "_insert_alias",
        fail_for_broken_alias,
    )

    with pytest.raises(RuntimeError):
        migrate_taxonomy_to_skill_registry(
            db_path=db_path,
        )

    assert list_skills(
        status=None,
        db_path=db_path,
    ) == []


def test_registry_survives_service_restart(tmp_path):
    db_path = tmp_path / "skills.db"
    save_skill(
        "Servicekatalog",
        aliases=[
            "Service Catalog",
        ],
        db_path=db_path,
    )

    reloaded = find_skill(
        "Service Catalog",
        db_path=db_path,
    )

    assert reloaded.canonical_name == "Servicekatalog"


def test_failed_insert_rolls_back(tmp_path, monkeypatch):
    db_path = tmp_path / "skills.db"

    def fail_insert_alias(*_args, **_kwargs):
        raise RuntimeError(
            "forced alias failure"
        )

    monkeypatch.setattr(
        "jobagent.services.skill_registry_service._insert_alias",
        fail_insert_alias,
    )

    with pytest.raises(RuntimeError):
        save_skill(
            "Rollback Skill",
            aliases=[
                "Rollback Alias",
            ],
            db_path=db_path,
        )

    assert list_skills(
        status=None,
        db_path=db_path,
    ) == []
