from __future__ import annotations

from pathlib import Path

from openllmbench.evaluators.human.review_loader import find_next_unreviewed_task
from openllmbench.evaluators.human.review_writer import review_path
from openllmbench.evaluators.human.rubric import load_rubric
from openllmbench.evaluators.human.scorecard import create_scorecard_from_rubric


def next_review_candidate(
    *,
    run_id: str,
    outputs_dir: str | Path = "benchmarks/outputs",
    reviews_dir: str | Path = "reviews",
) -> dict | None:
    return find_next_unreviewed_task(
        run_id=run_id,
        outputs_dir=outputs_dir,
        reviews_dir=reviews_dir,
    )


def create_blank_review(
    *,
    rubric_path: str | Path,
    run_id: str,
    model: str,
    task: str,
    reviewer: str,
):
    rubric = load_rubric(rubric_path)
    return create_scorecard_from_rubric(
        rubric=rubric,
        run_id=run_id,
        model=model,
        task=task,
        reviewer=reviewer,
    )


def default_review_path(*, reviews_dir: str | Path, run_id: str, model: str, task: str) -> Path:
    return review_path(reviews_dir=reviews_dir, run_id=run_id, model=model, task=task)

