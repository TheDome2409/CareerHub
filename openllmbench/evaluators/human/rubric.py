from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CRITERIA = (
    "Factual Correctness",
    "Hallucination Risk",
    "Completeness",
    "Structure",
    "Language",
    "Practical Usefulness",
    "Explainability",
    "Consistency",
)


@dataclass(frozen=True)
class RubricCriterion:
    id: str
    label: str
    description: str = ""
    min_score: int = 0
    max_score: int = 10


@dataclass(frozen=True)
class Rubric:
    id: str
    version: str
    title: str
    description: str = ""
    criteria: list[RubricCriterion] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def load_rubric(path: str | Path) -> Rubric:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    criteria = [
        RubricCriterion(
            id=str(item.get("id") or _slug(item.get("label", ""))),
            label=str(item.get("label", "")),
            description=str(item.get("description", "")),
            min_score=int(item.get("min_score", 0)),
            max_score=int(item.get("max_score", 10)),
        )
        for item in data.get("criteria", []) or []
    ]
    return Rubric(
        id=str(data.get("id", "")),
        version=str(data.get("version", "1.0")),
        title=str(data.get("title", "")),
        description=str(data.get("description", "")),
        criteria=criteria,
        metadata=dict(data.get("metadata", {}) or {}),
    )


def _slug(value: str) -> str:
    return "_".join(value.lower().strip().split())

