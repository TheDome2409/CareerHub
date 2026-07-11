from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _created_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _slug(value: str) -> str:
    result = []
    for char in value.lower().strip():
        if char.isalnum():
            result.append(char)
        elif char in {" ", "-", "_", ".", ":"}:
            result.append("_")
    slug = "".join(result).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "suite"


@dataclass
class CapabilityBuilder:
    capabilities: list[str] = field(default_factory=list)

    def add(self, capability_id: str) -> "CapabilityBuilder":
        if capability_id not in self.capabilities:
            self.capabilities.append(capability_id)
        return self

    def build(self) -> list[str]:
        return list(self.capabilities)


@dataclass
class PromptBuilder:
    template_id: str
    version: str = "0.1.0"
    template: str = "Write a structured answer for the task: {{ task }}"
    description: str = "Initial prompt template."

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.template_id,
            "version": self.version,
            "description": self.description,
            "template": self.template,
        }

    def write(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return output


@dataclass
class TaskBuilder:
    task_id: str
    prompt_template: str
    evaluation_profile: str
    version: str = "0.1.0"
    difficulty: str = "medium"
    capabilities: list[str] = field(default_factory=list)
    author: str = "OpenLLMBench"
    reviewed_at: str | None = None
    license: str = "TBD"
    tags: list[str] = field(default_factory=list)
    source: str = "suite_scaffold"
    expected_output: str = "structured_response"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.task_id,
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
            "metadata": {
                "scaffolded": True,
            },
        }

    def write(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return output


@dataclass
class DatasetBuilder:
    dataset_id: str
    name: str
    description: str
    semantic_version: str = "0.1.0"
    license: str = "TBD"
    tasks: list[TaskBuilder] = field(default_factory=list)

    def add_task(self, task: TaskBuilder) -> "DatasetBuilder":
        self.tasks.append(task)
        return self

    def manifest(self) -> dict[str, Any]:
        return {
            "id": self.dataset_id,
            "name": self.name,
            "description": self.description,
            "version": {
                "semantic_version": self.semantic_version,
                "hash": "",
                "created_at": _created_at(),
            },
            "license": self.license,
            "task_count": len(self.tasks),
            "metadata": {
                "status": "scaffold",
            },
        }

    def write(self, path: str | Path) -> Path:
        root = Path(path)
        (root / "tasks").mkdir(parents=True, exist_ok=True)
        (root / "media").mkdir(parents=True, exist_ok=True)
        (root / "references").mkdir(parents=True, exist_ok=True)
        (root / "media" / ".gitkeep").touch()
        (root / "references" / ".gitkeep").touch()
        (root / "dataset.yaml").write_text(
            yaml.safe_dump(self.manifest(), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        for task in self.tasks:
            task.write(root / "tasks" / f"{task.task_id}.yaml")
        return root


@dataclass
class BenchmarkSuiteBuilder:
    suite_name: str
    output_root: Path = Path("datasets")
    description: str | None = None
    capabilities: list[str] = field(default_factory=lambda: ["analysis", "reasoning"])
    author: str = "OpenLLMBench"
    evaluation_profile: str | None = None

    @property
    def suite_id(self) -> str:
        return _slug(self.suite_name)

    def build(self) -> dict[str, Path]:
        suite_id = self.suite_id
        suite_root = self.output_root / suite_id
        prompt_id = f"{suite_id}_prompt_v1"
        task_id = f"{suite_id}_sample_task"
        evaluation_profile = self.evaluation_profile or f"evaluation_profiles/{suite_id}.yaml"
        task = TaskBuilder(
            task_id=task_id,
            prompt_template=prompt_id,
            evaluation_profile=evaluation_profile,
            capabilities=self.capabilities,
            author=self.author,
            tags=[suite_id, "scaffold"],
        )
        dataset = DatasetBuilder(
            dataset_id=suite_id,
            name=self.suite_name,
            description=self.description or f"{self.suite_name} benchmark suite.",
            tasks=[task],
        )
        dataset.write(suite_root)
        prompts_dir = suite_root / "prompts"
        PromptBuilder(template_id=prompt_id).write(prompts_dir / f"{prompt_id}.yaml")
        self._write_readme(suite_root)
        self._write_docs(suite_root)
        self._write_tests(suite_root, suite_id)
        return {
            "suite_root": suite_root,
            "dataset": suite_root / "dataset.yaml",
            "task": suite_root / "tasks" / f"{task_id}.yaml",
            "prompt": prompts_dir / f"{prompt_id}.yaml",
            "readme": suite_root / "README.md",
            "docs": suite_root / "docs" / "README.md",
            "tests": suite_root / "tests" / f"test_{suite_id}_dataset.py",
        }

    def _write_readme(self, suite_root: Path) -> None:
        text = f"""# {self.suite_name}

This benchmark suite was scaffolded with the OpenLLMBench SDK.

## Purpose

{self.description or f"{self.suite_name} benchmark suite."}

## Structure

- `dataset.yaml`
- `tasks/`
- `prompts/`
- `media/`
- `references/`
- `docs/`
- `tests/`

## Next Steps

1. Replace the sample task with real benchmark tasks.
2. Review the prompt template.
3. Choose an evaluation profile.
4. Add references and media if needed.
"""
        (suite_root / "README.md").write_text(text, encoding="utf-8")

    def _write_docs(self, suite_root: Path) -> None:
        docs = suite_root / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "README.md").write_text(
            f"""# {self.suite_name} Suite Documentation

Document the suite purpose, task design, prompt strategy, review criteria and
known limitations here.
""",
            encoding="utf-8",
        )

    def _write_tests(self, suite_root: Path, suite_id: str) -> None:
        tests = suite_root / "tests"
        tests.mkdir(parents=True, exist_ok=True)
        (tests / f"test_{suite_id}_dataset.py").write_text(
            f"""from openllmbench.core.datasets import load_dataset


def test_{suite_id}_dataset_loads():
    dataset = load_dataset(r"{suite_root.as_posix()}")

    assert dataset.id == "{suite_id}"
    assert dataset.tasks
""",
            encoding="utf-8",
        )

