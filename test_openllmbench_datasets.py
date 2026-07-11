from pathlib import Path

import pytest

from openllmbench.core.datasets import load_dataset, load_dataset_task, stable_hash


DATASETS = ["careerhub", "coding", "documentation", "analysis"]


def test_dataset_directories_and_required_subfolders_exist():
    for dataset_id in DATASETS:
        root = Path("datasets") / dataset_id
        assert (root / "dataset.yaml").exists()
        assert (root / "tasks").is_dir()
        assert (root / "media").is_dir()
        assert (root / "references").is_dir()


def test_load_all_foundation_datasets():
    for dataset_id in DATASETS:
        dataset = load_dataset(Path("datasets") / dataset_id)
        assert dataset.id == dataset_id
        assert dataset.version.semantic_version == "0.1.0"
        assert dataset.version.hash
        assert dataset.version.created_at
        assert dataset.task_count == len(dataset.tasks)
        assert dataset.tasks


def test_dataset_task_contains_required_fields():
    task = load_dataset_task("datasets/careerhub/tasks/application_explainability.yaml")

    assert task.id == "careerhub_application_explainability"
    assert task.version == "0.1.0"
    assert task.difficulty == "medium"
    assert "career_matching" in task.capabilities
    assert task.prompt_template
    assert task.evaluation_profile == "evaluation_profiles/careerhub.yaml"
    assert task.author == "OpenLLMBench"
    assert task.license == "TBD"
    assert task.tags
    assert task.source
    assert task.expected_output


def test_dataset_hash_is_stable_for_same_input():
    first = load_dataset("datasets/coding")
    second = load_dataset("datasets/coding")

    assert first.version.hash == second.version.hash
    assert first.tasks[0].hash == second.tasks[0].hash


def test_stable_hash_changes_when_task_changes():
    original = load_dataset_task("datasets/documentation/tasks/readme_section.yaml")
    changed = {
        **original.to_dict(),
        "expected_output": "different_output",
    }

    assert original.hash != stable_hash(changed)


def test_missing_required_task_field_raises(tmp_path):
    path = tmp_path / "bad_task.yaml"
    path.write_text(
        """
id: bad
version: 0.1.0
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_dataset_task(path)
