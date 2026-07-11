import json
import subprocess
import sys

from openllmbench.evaluators.human.review_loader import find_next_unreviewed_task, load_review
from openllmbench.evaluators.human.review_writer import review_path, save_review
from openllmbench.evaluators.human.rubric import DEFAULT_CRITERIA, load_rubric
from openllmbench.evaluators.human.scorecard import create_scorecard_from_rubric


def test_load_rubric_contains_default_criteria():
    rubric = load_rubric("evaluation_profiles/careerhub.yaml")
    labels = [criterion.label for criterion in rubric.criteria]

    assert rubric.id == "careerhub"
    assert rubric.version == "1.0"
    assert labels == list(DEFAULT_CRITERIA)
    assert all(criterion.min_score == 0 for criterion in rubric.criteria)
    assert all(criterion.max_score == 10 for criterion in rubric.criteria)


def test_scorecard_calculates_overall_score():
    rubric = load_rubric("evaluation_profiles/coding.yaml")
    scorecard = create_scorecard_from_rubric(
        rubric=rubric,
        run_id="run",
        model="model",
        task="task",
        reviewer="Alex",
    )
    scorecard.criteria[0] = scorecard.criteria[0].__class__(
        criterion_id=scorecard.criteria[0].criterion_id,
        label=scorecard.criteria[0].label,
        score=10,
        comment="Good",
    )
    scorecard.criteria[1] = scorecard.criteria[1].__class__(
        criterion_id=scorecard.criteria[1].criterion_id,
        label=scorecard.criteria[1].label,
        score=6,
        comment=None,
    )

    assert scorecard.calculate_overall_score() == 8.0


def test_review_save_and_load_roundtrip(tmp_path):
    rubric = load_rubric("evaluation_profiles/documentation.yaml")
    scorecard = create_scorecard_from_rubric(
        rubric=rubric,
        run_id="run",
        model="qwen3:30b",
        task="docs_task",
        reviewer="human",
        comment="Initial review",
    )
    scorecard.criteria[0] = scorecard.criteria[0].__class__(
        criterion_id=scorecard.criteria[0].criterion_id,
        label=scorecard.criteria[0].label,
        score=9,
        comment="Accurate",
    )
    path = review_path(
        reviews_dir=tmp_path,
        run_id=scorecard.run_id,
        model=scorecard.model,
        task=scorecard.task,
    )

    save_review(scorecard, path)
    loaded = load_review(path)

    assert loaded.run_id == "run"
    assert loaded.model == "qwen3:30b"
    assert loaded.task == "docs_task"
    assert loaded.overall_score == 9.0
    assert loaded.criteria[0].comment == "Accurate"


def test_find_next_unreviewed_task(tmp_path):
    run_dir = tmp_path / "outputs" / "run" / "qwen3_30b"
    run_dir.mkdir(parents=True)
    (run_dir / "model_metadata.json").write_text(
        json.dumps({"model_name": "qwen3:30b"}),
        encoding="utf-8",
    )
    (run_dir / "task_a_run_1.json").write_text(
        json.dumps({"run_id": "run", "model": "qwen3:30b", "task_id": "task_a"}),
        encoding="utf-8",
    )

    candidate = find_next_unreviewed_task(
        run_id="run",
        outputs_dir=tmp_path / "outputs",
        reviews_dir=tmp_path / "reviews",
    )

    assert candidate["model"] == "qwen3:30b"
    assert candidate["task"] == "task_a"
    assert candidate["review_file"].endswith("task_a_review.yaml")


def test_openllmbench_review_cli_creates_blank_review(tmp_path):
    run_dir = tmp_path / "outputs" / "run" / "model_1"
    run_dir.mkdir(parents=True)
    (run_dir / "model_metadata.json").write_text(
        json.dumps({"model_name": "model:1"}),
        encoding="utf-8",
    )
    (run_dir / "task_run_1.json").write_text(
        json.dumps({"run_id": "run", "model": "model:1", "task_id": "task"}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "openllmbench",
            "review",
            "--run-id",
            "run",
            "--outputs-dir",
            str(tmp_path / "outputs"),
            "--reviews-dir",
            str(tmp_path / "reviews"),
            "--rubric",
            "evaluation_profiles/analysis.yaml",
            "--reviewer",
            "tester",
            "--create",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Next unreviewed task" in result.stdout
    assert "Created blank review" in result.stdout
    assert (tmp_path / "reviews" / "run" / "model_1" / "task_review.yaml").exists()
