import json
from pathlib import Path

from careerhub.benchmark_models import (
    BenchmarkConfig,
    BenchmarkModel,
    BenchmarkSettings,
    BenchmarkTask,
    BenchmarkTaskSet,
    load_benchmark_config,
    load_benchmark_task_set,
    safe_model_name,
)
from careerhub.benchmark_metadata import git_metadata, make_run_id
from careerhub.benchmark_runner import run_benchmark
from careerhub.ollama_client import OllamaGenerateResult


class FakeOllamaClient:
    def __init__(self):
        self.calls = []

    def generate(self, *, model, prompt, keep_alive, options):
        self.calls.append(
            {
                "model": model,
                "prompt": prompt,
                "keep_alive": keep_alive,
                "options": options,
            }
        )
        return OllamaGenerateResult(
            response=f"response from {model}: {prompt[:12]}",
            duration_seconds=1.5,
            error=None,
            raw={
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 3,
                "eval_count": 6,
                "prompt_eval_duration": 1_000_000_000,
                "eval_duration": 2_000_000_000,
                "load_duration": 100_000_000,
                "total_duration": 4_000_000_000,
            },
        )

    def get_model_metadata(self, model_name):
        return {
            "name": model_name,
            "tag": model_name.rsplit(":", 1)[-1] if ":" in model_name else None,
            "digest": f"sha256:{model_name}",
            "details": {"family": "test"},
            "raw": {"name": model_name},
        }

    def get_ollama_version(self):
        return "0.0-test"


def _task(task_id: str, category: str = "careerhub") -> BenchmarkTask:
    return BenchmarkTask(
        id=task_id,
        category=category,
        title=f"Task {task_id}",
        prompt=f"Prompt {task_id}",
        expected_output_type="text",
        task_version="1.0",
        prompt_version="1.0",
        evaluation_hints=["hint"],
    )


def test_load_benchmark_config(tmp_path):
    config_path = tmp_path / "benchmark_models.yaml"
    config_path.write_text(
        """
models:
  - name: qwen3:14b
    runs: 2
    keep_alive: "30m"
settings:
  temperature: 0.3
  top_p: 0.8
  num_ctx: 4096
  timeout_seconds: 123
  tasks_path: benchmarks/prompts/benchmark_tasks.yaml
""",
        encoding="utf-8",
    )

    config = load_benchmark_config(config_path)

    assert config.models[0].name == "qwen3:14b"
    assert config.models[0].runs == 2
    assert config.settings.temperature == 0.3
    assert config.settings.ollama_options["num_ctx"] == 4096


def test_load_benchmark_task_set_versions(tmp_path):
    task_path = tmp_path / "tasks.yaml"
    task_path.write_text(
        """
suite_version: "2.0"
task_set_version: "2.1"
prompt_set_version: "2.2"
tasks:
  - id: sample
    task_version: "3.0"
    prompt_version: "3.1"
    category: coding
    title: Sample
    prompt: Say hi
    expected_output_type: text
""",
        encoding="utf-8",
    )

    task_set = load_benchmark_task_set(task_path)

    assert task_set.suite_version == "2.0"
    assert task_set.task_set_version == "2.1"
    assert task_set.prompt_set_version == "2.2"
    assert task_set.tasks[0].task_version == "3.0"
    assert task_set.tasks[0].prompt_version == "3.1"
    assert task_set.task_file_hash is not None


def test_safe_model_name():
    assert safe_model_name("qwen3:14b") == "qwen3_14b"
    assert safe_model_name("deepseek-r1:32b") == "deepseek_r1_32b"
    assert safe_model_name("some/model name") == "some_model_name"


def test_run_id_is_valid_with_label():
    run_id = make_run_id("July 2026 Baseline", "20260709_120000")

    assert run_id == "20260709_120000_july_2026_baseline"


def test_task_and_prompt_hashes_are_stable_and_change_on_prompt_change():
    first = _task("same")
    second = _task("same")
    changed = BenchmarkTask(
        id="same",
        category="careerhub",
        title="Task same",
        prompt="Changed prompt",
        expected_output_type="text",
        task_version="1.0",
        prompt_version="1.0",
        evaluation_hints=["hint"],
    )

    assert first.task_hash == second.task_hash
    assert first.prompt_hash == second.prompt_hash
    assert first.prompt_hash != changed.prompt_hash
    assert first.task_hash != changed.task_hash


def test_runner_groups_by_model_and_writes_outputs(tmp_path):
    config = BenchmarkConfig(
        models=[
            BenchmarkModel(name="model-a:1", runs=2, keep_alive="10m"),
            BenchmarkModel(name="model-b:1", runs=2, keep_alive="10m"),
        ],
        settings=BenchmarkSettings(temperature=0.2, top_p=0.9, num_ctx=1024),
    )
    tasks = [_task("task_a"), _task("task_b", "coding")]
    client = FakeOllamaClient()

    task_set = BenchmarkTaskSet(
        suite_version="suite-a",
        task_set_version="tasks-a",
        prompt_set_version="prompts-a",
        task_file_hash="task-file-hash",
        tasks=tasks,
    )

    summary = run_benchmark(
        config=config,
        tasks=task_set,
        client=client,
        output_dir=tmp_path / "outputs",
        report_dir=tmp_path / "reports",
        timestamp="20260709_120000",
        no_archive=True,
    )

    assert [call["model"] for call in client.calls] == [
        "model-a:1",
        "model-a:1",
        "model-a:1",
        "model-a:1",
        "model-b:1",
        "model-b:1",
        "model-b:1",
        "model-b:1",
    ]
    assert summary.model_order == ["model-a:1", "model-b:1"]
    output_file = tmp_path / "outputs" / "20260709_120000" / "model_a_1" / "task_a_run_1.json"
    assert output_file.exists()
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload["run_id"] == "20260709_120000"
    assert payload["model"] == "model-a:1"
    assert payload["model_digest"] == "sha256:model-a:1"
    assert payload["task_id"] == "task_a"
    assert payload["task_version"] == "1.0"
    assert payload["prompt_version"] == "1.0"
    assert payload["task_hash"]
    assert payload["prompt_hash"]
    assert payload["config_hash"]
    assert payload["benchmark_suite_version"] == "suite-a"
    assert payload["careerhub_version"]
    assert "git_dirty_state" in payload
    assert payload["metadata"]["keep_alive"] == "10m"
    assert payload["metrics"]["token_metrics"]["prompt_tokens"] == 3
    assert payload["metrics"]["token_metrics"]["completion_tokens"] == 6
    assert payload["metrics"]["timing_metrics"]["generation_time_ms"] == 2000.0
    assert (tmp_path / "outputs" / "20260709_120000" / "run_metadata.json").exists()
    assert (tmp_path / "outputs" / "20260709_120000" / "model_a_1" / "model_metadata.json").exists()
    assert (tmp_path / "outputs" / "20260709_120000" / "model_a_1" / "metrics_summary.json").exists()
    assert (tmp_path / "outputs" / "20260709_120000" / "run_summary.json").exists()
    assert (tmp_path / "reports" / "20260709_120000_metrics.csv").exists()


def test_runner_filters_models_runs_and_categories(tmp_path):
    config = BenchmarkConfig(
        models=[
            BenchmarkModel(name="qwen3:14b", runs=5),
            BenchmarkModel(name="gemma3:27b", runs=5),
        ],
        settings=BenchmarkSettings(),
    )
    tasks = [_task("careerhub_task", "careerhub"), _task("coding_task", "coding")]
    client = FakeOllamaClient()

    run_benchmark(
        config=config,
        tasks=tasks,
        client=client,
        output_dir=tmp_path / "outputs",
        report_dir=tmp_path / "reports",
        selected_models=["gemma3:27b"],
        runs_override=1,
        selected_categories=["coding"],
        timestamp="20260709_130000",
        no_archive=True,
    )

    assert len(client.calls) == 1
    assert client.calls[0]["model"] == "gemma3:27b"
    assert client.calls[0]["prompt"] == "Prompt coding_task"


def test_report_is_created(tmp_path):
    config = BenchmarkConfig(
        models=[BenchmarkModel(name="qwen3:14b", runs=1)],
        settings=BenchmarkSettings(),
    )
    client = FakeOllamaClient()

    summary = run_benchmark(
        config=config,
        tasks=[_task("task_a")],
        client=client,
        output_dir=tmp_path / "outputs",
        report_dir=tmp_path / "reports",
        timestamp="20260709_140000",
        no_archive=True,
    )

    assert summary.report_path is not None
    report = Path(summary.report_path).read_text(encoding="utf-8")
    assert "CareerHub LLM Benchmark Summary" in report
    assert "Erfolgreich: 1" in report
    assert "qwen3:14b" in report
    assert "Run ID: `20260709_140000`" in report
    assert "Config Hash:" in report


def test_resume_skips_existing_outputs(tmp_path):
    config = BenchmarkConfig(
        models=[BenchmarkModel(name="qwen3:14b", runs=1)],
        settings=BenchmarkSettings(),
    )
    task = _task("task_a")
    first_client = FakeOllamaClient()
    run_benchmark(
        config=config,
        tasks=[task],
        client=first_client,
        output_dir=tmp_path / "outputs",
        report_dir=tmp_path / "reports",
        run_id="resume_run",
        no_archive=True,
    )

    second_client = FakeOllamaClient()
    summary = run_benchmark(
        config=config,
        tasks=[task],
        client=second_client,
        output_dir=tmp_path / "outputs",
        report_dir=tmp_path / "reports",
        resume="resume_run",
        no_archive=True,
    )

    assert second_client.calls == []
    assert summary.records[0].metadata["resumed"] is True


def test_git_metadata_outside_git_repo_does_not_crash(tmp_path):
    metadata = git_metadata(tmp_path)

    assert metadata.commit_hash is None
    assert metadata.dirty_state == "unknown"
