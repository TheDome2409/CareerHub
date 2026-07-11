from __future__ import annotations

import json
from pathlib import Path

import yaml

from openllmbench.evaluators.human.scorecard import Scorecard
from openllmbench.evaluators.human.review_writer import review_path


def load_review(path: str | Path) -> Scorecard:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return Scorecard.from_dict(data)


def find_next_unreviewed_task(
    *,
    run_id: str,
    outputs_dir: str | Path = "benchmarks/outputs",
    reviews_dir: str | Path = "reviews",
) -> dict | None:
    run_dir = Path(outputs_dir) / run_id
    if not run_dir.exists():
        return None
    for model_dir in sorted(path for path in run_dir.iterdir() if path.is_dir()):
        model_metadata = model_dir / "model_metadata.json"
        if not model_metadata.exists():
            continue
        model_name = _model_name(model_metadata, model_dir.name)
        for task_file in sorted(model_dir.glob("*_run_*.json")):
            payload = json.loads(task_file.read_text(encoding="utf-8"))
            task_id = str(payload.get("task_id") or task_file.stem)
            path = review_path(
                reviews_dir=reviews_dir,
                run_id=run_id,
                model=model_name,
                task=task_id,
            )
            if not path.exists():
                return {
                    "run_id": run_id,
                    "model": model_name,
                    "task": task_id,
                    "task_file": str(task_file),
                    "review_file": str(path),
                }
    return None


def _model_name(path: Path, fallback: str) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return str(data.get("model_name") or fallback)
    except Exception:
        return fallback

