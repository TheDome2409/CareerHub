import io
import json
from pathlib import Path

from careerhub.benchmark_models import BenchmarkConfig, BenchmarkModel, BenchmarkSettings, BenchmarkTask
from careerhub.benchmark_progress import BenchmarkProgressTracker
from careerhub.benchmark_runner import run_benchmark
from careerhub.ollama_client import OllamaGenerateResult


class FakeOllamaClient:
    def generate(self, *, model, prompt, keep_alive, options):
        return OllamaGenerateResult(
            response="ok",
            duration_seconds=2.0,
            error=None,
            raw={
                "prompt_eval_count": 10,
                "eval_count": 30,
                "eval_duration": 1_000_000_000,
                "total_duration": 2_000_000_000,
            },
        )

    def get_model_metadata(self, model_name):
        return {"name": model_name, "tag": "1", "digest": None, "details": {}, "raw": {}}

    def get_ollama_version(self):
        return None


def _task(task_id="task") -> BenchmarkTask:
    return BenchmarkTask(
        id=task_id,
        category="coding",
        title="Task",
        prompt="Prompt",
        expected_output_type="text",
    )


def test_progress_state_percent_and_eta(tmp_path):
    tracker = BenchmarkProgressTracker(
        output_dir=tmp_path,
        run_id="run",
        run_label=None,
        total_models=1,
        total_tasks=2,
        total_task_runs=4,
        mode="json_only",
    )

    tracker.start_run()
    tracker.finish_task(
        model="m",
        task_id="task",
        run_number=1,
        duration_seconds=1.0,
        metrics={},
    )

    assert tracker.state.percent_complete == 25.0
    assert tracker.state.estimated_total_seconds is not None
    assert tracker.state.eta_seconds is not None
    assert tracker.state.eta_human is not None


def test_progress_events_are_append_only_and_state_updates(tmp_path):
    tracker = BenchmarkProgressTracker(
        output_dir=tmp_path,
        run_id="run",
        run_label="label",
        total_models=1,
        total_tasks=1,
        total_task_runs=1,
        mode="json_only",
    )

    tracker.start_run()
    tracker.start_model("model")
    tracker.finish_run()

    events = (tmp_path / "progress_events.jsonl").read_text(encoding="utf-8").splitlines()
    state = json.loads((tmp_path / "progress_state.json").read_text(encoding="utf-8"))

    assert len(events) == 3
    assert json.loads(events[0])["event_type"] == "run_started"
    assert json.loads(events[-1])["event_type"] == "run_finished"
    assert state["current_phase"] == "finished"


def test_progress_write_errors_do_not_crash(tmp_path):
    file_path = tmp_path / "not_a_dir"
    file_path.write_text("x", encoding="utf-8")
    tracker = BenchmarkProgressTracker(
        output_dir=file_path,
        run_id="run",
        run_label=None,
        total_models=1,
        total_tasks=1,
        total_task_runs=1,
        mode="json_only",
    )

    tracker.start_run()
    tracker.finish_run()

    assert tracker.state.current_phase == "finished"


def test_runner_writes_progress_files(tmp_path):
    config = BenchmarkConfig(
        models=[BenchmarkModel(name="model:1", runs=1)],
        settings=BenchmarkSettings(),
    )

    summary = run_benchmark(
        config=config,
        tasks=[_task()],
        client=FakeOllamaClient(),
        output_dir=tmp_path / "outputs",
        report_dir=tmp_path / "reports",
        run_id="progress_run",
        no_archive=True,
        progress_mode="json_only",
    )

    state_path = summary.output_root / "progress_state.json"
    events_path = summary.output_root / "progress_events.jsonl"
    assert state_path.exists()
    assert events_path.exists()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["percent_complete"] == 100.0
    assert state["current_phase"] == "finished"
    assert "## Progress Summary" in Path(summary.report_path).read_text(encoding="utf-8")


def test_quiet_suppresses_normal_progress_output(tmp_path):
    stream = io.StringIO()
    tracker = BenchmarkProgressTracker(
        output_dir=tmp_path,
        run_id="run",
        run_label=None,
        total_models=1,
        total_tasks=1,
        total_task_runs=1,
        mode="quiet",
        stream=stream,
    )

    tracker.start_run()
    tracker.start_model("model")
    tracker.finish_run()

    output = stream.getvalue()
    assert "Model" not in output
    assert "Run finished" in output


def test_json_only_writes_files_without_terminal_output(tmp_path):
    stream = io.StringIO()
    tracker = BenchmarkProgressTracker(
        output_dir=tmp_path,
        run_id="run",
        run_label=None,
        total_models=1,
        total_tasks=1,
        total_task_runs=1,
        mode="json_only",
        stream=stream,
    )

    tracker.start_run()

    assert stream.getvalue() == ""
    assert (tmp_path / "progress_state.json").exists()
    assert (tmp_path / "progress_events.jsonl").exists()
