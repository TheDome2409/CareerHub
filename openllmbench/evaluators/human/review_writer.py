from __future__ import annotations

from pathlib import Path

import yaml

from openllmbench.evaluators.human.scorecard import Scorecard


def review_path(
    *,
    reviews_dir: str | Path,
    run_id: str,
    model: str,
    task: str,
) -> Path:
    safe_model = _safe_path(model)
    return Path(reviews_dir) / run_id / safe_model / f"{task}_review.yaml"


def save_review(scorecard: Scorecard, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        yaml.safe_dump(scorecard.to_dict(), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return output


def _safe_path(value: str) -> str:
    result = []
    for char in value.lower().strip():
        if char.isalnum():
            result.append(char)
        elif char in {":", "/", "\\", " ", ".", "-"}:
            result.append("_")
    safe = "".join(result).strip("_")
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe or "model"

