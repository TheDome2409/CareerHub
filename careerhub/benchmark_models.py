from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from careerhub.benchmark_metadata import stable_file_hash, stable_json_hash, stable_text_hash


DEFAULT_TASKS_PATH = Path("benchmarks") / "prompts" / "benchmark_tasks.yaml"


@dataclass(frozen=True)
class BenchmarkModel:
    name: str
    runs: int = 1
    keep_alive: str = "30m"


@dataclass(frozen=True)
class BenchmarkSettings:
    temperature: float = 0.2
    top_p: float = 0.9
    num_ctx: int = 8192
    timeout_seconds: int = 600
    tasks_path: Path = DEFAULT_TASKS_PATH

    @property
    def ollama_options(self) -> dict[str, Any]:
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "num_ctx": self.num_ctx,
        }


@dataclass(frozen=True)
class BenchmarkTask:
    id: str
    category: str
    title: str
    prompt: str
    expected_output_type: str
    task_version: str = "1.0"
    prompt_version: str = "1.0"
    evaluation_hints: list[str] = field(default_factory=list)

    @property
    def task_hash(self) -> str:
        return stable_json_hash(
            {
                "id": self.id,
                "category": self.category,
                "title": self.title,
                "prompt": self.prompt,
                "expected_output_type": self.expected_output_type,
                "task_version": self.task_version,
                "prompt_version": self.prompt_version,
                "evaluation_hints": self.evaluation_hints,
            }
        )

    @property
    def prompt_hash(self) -> str:
        return stable_text_hash(self.prompt)


@dataclass(frozen=True)
class BenchmarkConfig:
    models: list[BenchmarkModel]
    settings: BenchmarkSettings
    config_hash: str | None = None


@dataclass(frozen=True)
class BenchmarkTaskSet:
    suite_version: str = "1.0"
    task_set_version: str = "1.0"
    prompt_set_version: str = "1.0"
    task_file_hash: str | None = None
    tasks: list[BenchmarkTask] = field(default_factory=list)


def safe_model_name(model_name: str) -> str:
    safe = []
    for char in model_name.lower().strip():
        if char.isalnum():
            safe.append(char)
        elif char in {":", "/", "\\", " ", ".", "-"}:
            safe.append("_")
    result = "".join(safe).strip("_")
    while "__" in result:
        result = result.replace("__", "_")
    return result or "model"


def load_benchmark_config(path: str | Path) -> BenchmarkConfig:
    config_path = Path(path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    model_items = data.get("models") or []
    settings_data = data.get("settings") or {}

    models = [
        BenchmarkModel(
            name=str(item["name"]),
            runs=int(item.get("runs", 1)),
            keep_alive=str(item.get("keep_alive", "30m")),
        )
        for item in model_items
        if item.get("name")
    ]
    settings = BenchmarkSettings(
        temperature=float(settings_data.get("temperature", 0.2)),
        top_p=float(settings_data.get("top_p", 0.9)),
        num_ctx=int(settings_data.get("num_ctx", 8192)),
        timeout_seconds=int(settings_data.get("timeout_seconds", 600)),
        tasks_path=Path(settings_data.get("tasks_path", DEFAULT_TASKS_PATH)),
    )
    return BenchmarkConfig(
        models=models,
        settings=settings,
        config_hash=stable_file_hash(config_path) or stable_json_hash(data),
    )


def load_benchmark_task_set(path: str | Path = DEFAULT_TASKS_PATH) -> BenchmarkTaskSet:
    tasks_path = Path(path)
    data = yaml.safe_load(tasks_path.read_text(encoding="utf-8")) or {}
    tasks = []
    for item in data.get("tasks") or []:
        tasks.append(
            BenchmarkTask(
                id=str(item["id"]),
                category=str(item["category"]),
                title=str(item["title"]),
                prompt=str(item["prompt"]),
                expected_output_type=str(item.get("expected_output_type", "")),
                task_version=str(item.get("task_version", data.get("task_set_version", "1.0"))),
                prompt_version=str(item.get("prompt_version", data.get("prompt_set_version", "1.0"))),
                evaluation_hints=[
                    str(value)
                    for value in item.get("evaluation_hints", []) or []
                ],
            )
        )
    return BenchmarkTaskSet(
        suite_version=str(data.get("suite_version", "1.0")),
        task_set_version=str(data.get("task_set_version", "1.0")),
        prompt_set_version=str(data.get("prompt_set_version", "1.0")),
        task_file_hash=stable_file_hash(tasks_path),
        tasks=tasks,
    )


def load_benchmark_tasks(path: str | Path = DEFAULT_TASKS_PATH) -> list[BenchmarkTask]:
    return load_benchmark_task_set(path).tasks
