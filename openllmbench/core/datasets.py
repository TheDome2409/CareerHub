from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class DatasetTask:
    id: str
    version: str
    difficulty: str
    capabilities: list[str]
    prompt_template: str
    evaluation_profile: str
    author: str
    reviewed_at: str | None
    license: str
    tags: list[str]
    source: str | None
    expected_output: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def hash(self) -> str:
        return stable_hash(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "difficulty": self.difficulty,
            "capabilities": self.capabilities,
            "prompt_template": self.prompt_template,
            "evaluation_profile": self.evaluation_profile,
            "author": self.author,
            "reviewed_at": self.reviewed_at,
            "license": self.license,
            "tags": self.tags,
            "source": self.source,
            "expected_output": self.expected_output,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class DatasetVersion:
    semantic_version: str
    hash: str
    created_at: str


@dataclass(frozen=True)
class BenchmarkDataset:
    id: str
    name: str
    description: str
    version: DatasetVersion
    license: str
    task_count: int
    tasks: list[DatasetTask]
    path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


def load_dataset(path: str | Path) -> BenchmarkDataset:
    dataset_path = Path(path)
    manifest_path = dataset_path / "dataset.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    tasks = [
        load_dataset_task(task_path)
        for task_path in sorted((dataset_path / "tasks").glob("*.yaml"))
    ]
    calculated_hash = stable_hash(
        {
            "manifest": manifest,
            "tasks": [task.to_dict() for task in tasks],
        }
    )
    version_data = manifest.get("version") or {}
    version = DatasetVersion(
        semantic_version=str(version_data.get("semantic_version", "0.1.0")),
        hash=str(version_data.get("hash") or calculated_hash),
        created_at=str(version_data.get("created_at", "")),
    )
    return BenchmarkDataset(
        id=str(manifest.get("id", dataset_path.name)),
        name=str(manifest.get("name", dataset_path.name)),
        description=str(manifest.get("description", "")),
        version=version,
        license=str(manifest.get("license", "")),
        task_count=int(manifest.get("task_count", len(tasks))),
        tasks=tasks,
        path=dataset_path,
        metadata=dict(manifest.get("metadata", {}) or {}),
    )


def load_dataset_task(path: str | Path) -> DatasetTask:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    required = [
        "id",
        "version",
        "difficulty",
        "capabilities",
        "prompt_template",
        "evaluation_profile",
        "author",
        "license",
        "tags",
        "expected_output",
    ]
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"Dataset task {path} misses required fields: {', '.join(missing)}")
    return DatasetTask(
        id=str(data["id"]),
        version=str(data["version"]),
        difficulty=str(data["difficulty"]),
        capabilities=[str(value) for value in data.get("capabilities") or []],
        prompt_template=str(data["prompt_template"]),
        evaluation_profile=str(data["evaluation_profile"]),
        author=str(data["author"]),
        reviewed_at=data.get("reviewed_at"),
        license=str(data["license"]),
        tags=[str(value) for value in data.get("tags") or []],
        source=data.get("source"),
        expected_output=str(data["expected_output"]),
        metadata=dict(data.get("metadata", {}) or {}),
    )


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

