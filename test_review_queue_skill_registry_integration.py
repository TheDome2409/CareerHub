from jobagent.services import companyhub_db_service
from jobagent.services.review_queue_service import (
    add_review_candidates,
    review_item_key,
    update_review_status,
)
from jobagent.services.skill_registry_service import (
    find_skill,
    list_skills,
    save_skill,
)


def _candidate(name: str, candidate_type: str = "skill") -> dict:
    return {
        "name": name,
        "canonical_name": name,
        "suggested_tag": name.lower().replace(" ", "_"),
        "candidate_type": candidate_type,
        "confidence": 0.9,
        "is_skill": True,
    }


def test_review_approval_writes_skill_registry(
    tmp_path,
    monkeypatch,
):
    queue_path = tmp_path / "review_queue.json"
    db_path = tmp_path / "companyhub.db"
    monkeypatch.setattr(
        "jobagent.services.review_queue_service.REVIEW_QUEUE_FILE",
        queue_path,
    )
    monkeypatch.setattr(
        companyhub_db_service,
        "DEFAULT_COMPANYHUB_DB_PATH",
        db_path,
    )

    queue = add_review_candidates(
        [
            _candidate(
                "Azure Landing Zones"
            )
        ]
    )
    item_key = review_item_key(
        queue[0]
    )

    updated = update_review_status(
        item_key,
        "approved",
        canonical_name="Azure Landing Zone",
        aliases=[
            "azure landingzone",
        ],
    )

    skill = find_skill(
        "azure landingzone",
        db_path=db_path,
    )
    assert skill.canonical_name == "Azure Landing Zone"
    assert updated[0]["status"] == "approved"
    assert updated[0]["registry_skill_id"] == skill.id


def test_review_conflict_keeps_item_pending(
    tmp_path,
    monkeypatch,
):
    queue_path = tmp_path / "review_queue.json"
    db_path = tmp_path / "companyhub.db"
    monkeypatch.setattr(
        "jobagent.services.review_queue_service.REVIEW_QUEUE_FILE",
        queue_path,
    )
    monkeypatch.setattr(
        companyhub_db_service,
        "DEFAULT_COMPANYHUB_DB_PATH",
        db_path,
    )
    save_skill(
        "Azure Landing Zone",
        skill_type="skill",
        db_path=db_path,
    )
    queue = add_review_candidates(
        [
            _candidate(
                "Azure Landing Zone",
                "certification",
            )
        ]
    )
    item_key = review_item_key(
        queue[0]
    )

    updated = update_review_status(
        item_key,
        "approved",
        candidate_type="certification",
    )

    assert updated[0]["status"] == "pending"
    assert updated[0]["registry_conflict"]["existing_type"] == "skill"


def test_review_rejection_does_not_create_registry_entry(
    tmp_path,
    monkeypatch,
):
    queue_path = tmp_path / "review_queue.json"
    db_path = tmp_path / "companyhub.db"
    monkeypatch.setattr(
        "jobagent.services.review_queue_service.REVIEW_QUEUE_FILE",
        queue_path,
    )
    monkeypatch.setattr(
        companyhub_db_service,
        "DEFAULT_COMPANYHUB_DB_PATH",
        db_path,
    )

    queue = add_review_candidates(
        [
            _candidate(
                "Generic Noise"
            )
        ]
    )
    item_key = review_item_key(
        queue[0]
    )

    updated = update_review_status(
        item_key,
        "rejected",
    )

    assert updated[0]["status"] == "rejected"
    assert updated[0]["registry_action"] == "rejected"
    assert "registry_skill_id" not in updated[0]
    assert list_skills(
        status=None,
        db_path=db_path,
    ) == []


def test_review_queue_save_failure_rolls_back_created_skill(
    tmp_path,
    monkeypatch,
):
    queue_path = tmp_path / "review_queue.json"
    db_path = tmp_path / "companyhub.db"
    monkeypatch.setattr(
        "jobagent.services.review_queue_service.REVIEW_QUEUE_FILE",
        queue_path,
    )
    monkeypatch.setattr(
        companyhub_db_service,
        "DEFAULT_COMPANYHUB_DB_PATH",
        db_path,
    )
    queue = add_review_candidates(
        [
            _candidate(
                "Rollback Skill"
            )
        ]
    )
    item_key = review_item_key(
        queue[0]
    )

    def fail_save(_items):
        raise RuntimeError(
            "forced queue save failure"
        )

    monkeypatch.setattr(
        "jobagent.services.review_queue_service.save_review_queue",
        fail_save,
    )

    import pytest

    with pytest.raises(RuntimeError):
        update_review_status(
            item_key,
            "approved",
        )

    assert find_skill(
        "Rollback Skill",
        db_path=db_path,
    ) is None


def test_review_queue_save_failure_rolls_back_merged_alias(
    tmp_path,
    monkeypatch,
):
    queue_path = tmp_path / "review_queue.json"
    db_path = tmp_path / "companyhub.db"
    monkeypatch.setattr(
        "jobagent.services.review_queue_service.REVIEW_QUEUE_FILE",
        queue_path,
    )
    monkeypatch.setattr(
        companyhub_db_service,
        "DEFAULT_COMPANYHUB_DB_PATH",
        db_path,
    )
    existing = save_skill(
        "Azure Landing Zone",
        aliases=[
            "Original Azure Alias",
        ],
        db_path=db_path,
    )
    queue = add_review_candidates(
        [
            _candidate(
                "New Azure Alias"
            )
        ]
    )
    item_key = review_item_key(
        queue[0]
    )

    def fail_save(_items):
        raise RuntimeError(
            "forced queue save failure"
        )

    monkeypatch.setattr(
        "jobagent.services.review_queue_service.save_review_queue",
        fail_save,
    )

    import pytest

    with pytest.raises(RuntimeError):
        update_review_status(
            item_key,
            "approved",
            existing_skill_id=existing.entry.id,
        )

    assert find_skill(
        "Original Azure Alias",
        db_path=db_path,
    ).id == existing.entry.id
    assert find_skill(
        "New Azure Alias",
        db_path=db_path,
    ) is None
