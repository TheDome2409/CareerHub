import importlib.util

import pytest

from careerhub.benchmark_archive import BenchmarkArchive
from careerhub.benchmark_models import BenchmarkConfig, BenchmarkModel, BenchmarkSettings, BenchmarkTask
from careerhub.benchmark_runner import run_benchmark
from careerhub.ollama_client import OllamaGenerateResult


duckdb_available = importlib.util.find_spec("duckdb") is not None


class FakeOllamaClient:
    def generate(self, *, model, prompt, keep_alive, options):
        return OllamaGenerateResult(
            response="Archivantwort",
            duration_seconds=1.0,
            error=None,
            raw={
                "prompt_eval_count": 4,
                "eval_count": 8,
                "prompt_eval_duration": 1_000_000_000,
                "eval_duration": 2_000_000_000,
                "load_duration": 100_000_000,
                "total_duration": 4_000_000_000,
                "done": True,
            },
        )

    def get_model_metadata(self, model_name):
        return {
            "name": model_name,
            "tag": "1",
            "digest": "sha256:test",
            "details": {"parameter_size": "7B", "quantization_level": "Q4_K_M"},
            "raw": {"name": model_name},
        }

    def get_ollama_version(self):
        return "test"


def _task() -> BenchmarkTask:
    return BenchmarkTask(
        id="archive_task",
        category="coding",
        title="Archive Task",
        prompt="Prompt",
        expected_output_type="text",
        task_version="1.0",
        prompt_version="1.0",
    )


def _create_run(tmp_path):
    config = BenchmarkConfig(
        models=[BenchmarkModel(name="archive-model:1", runs=1)],
        settings=BenchmarkSettings(),
    )
    summary = run_benchmark(
        config=config,
        tasks=[_task()],
        client=FakeOllamaClient(),
        output_dir=tmp_path / "outputs",
        report_dir=tmp_path / "reports",
        run_id="archive_run",
        no_archive=True,
    )
    return summary


@pytest.mark.skipif(not duckdb_available, reason="duckdb is not installed")
def test_archive_schema_and_run_metadata(tmp_path):
    summary = _create_run(tmp_path)
    archive = BenchmarkArchive(tmp_path / "archive.duckdb")

    archive_summary = archive.archive_run(summary.output_root)

    assert archive_summary.archived_models == 1
    assert archive_summary.archived_tasks == 1
    assert archive_summary.archived_metrics == 1
    run = archive.get_run("archive_run")
    assert run["run_id"] == "archive_run"


@pytest.mark.skipif(not duckdb_available, reason="duckdb is not installed")
def test_archive_is_idempotent(tmp_path):
    summary = _create_run(tmp_path)
    archive = BenchmarkArchive(tmp_path / "archive.duckdb")

    archive.archive_run(summary.output_root)
    archive.archive_run(summary.output_root)

    models = archive.compare_models("archive_run")
    assert len(models) == 1
    assert models[0]["task_runs"] == 1


@pytest.mark.skipif(not duckdb_available, reason="duckdb is not installed")
def test_archive_list_runs_and_compare_runs(tmp_path):
    summary = _create_run(tmp_path)
    archive = BenchmarkArchive(tmp_path / "archive.duckdb")
    archive.archive_run(summary.output_root)

    runs = archive.list_runs()
    comparison = archive.compare_runs(["archive_run"])

    assert runs[0]["run_id"] == "archive_run"
    assert comparison[0]["run_id"] == "archive_run"
    assert comparison[0]["total_tokens"] == 12


def test_archive_without_duckdb_is_safe(tmp_path, monkeypatch):
    import careerhub.benchmark_archive as archive_module

    monkeypatch.setattr(archive_module, "duckdb", None)
    archive = BenchmarkArchive(tmp_path / "archive.duckdb")
    summary = archive.archive_run(tmp_path / "outputs" / "missing")

    assert summary.warnings == ["DuckDB nicht installiert, Archivierung übersprungen."]
