import csv
from types import SimpleNamespace

from careerhub.benchmark_metrics import (
    aggregate_model_metrics,
    build_benchmark_metrics,
    write_metrics_csv,
)


def test_metrics_calculate_tps_ratios_and_characters_per_token():
    metrics = build_benchmark_metrics(
        prompt="hello world",
        response="good answer",
        raw={
            "prompt_eval_count": 2,
            "eval_count": 5,
            "prompt_eval_duration": 1_000_000_000,
            "eval_duration": 2_000_000_000,
            "load_duration": 500_000_000,
            "total_duration": 4_000_000_000,
            "done": True,
            "done_reason": "stop",
            "created_at": "2026-07-09T12:00:00Z",
            "context": [1, 2, 3],
        },
    )

    assert metrics["token_metrics"]["prompt_tokens"] == 2
    assert metrics["token_metrics"]["completion_tokens"] == 5
    assert metrics["token_metrics"]["total_tokens"] == 7
    assert metrics["token_metrics"]["prompt_completion_ratio"] == 0.4
    assert metrics["performance_metrics"]["prompt_tokens_per_second"] == 2.0
    assert metrics["performance_metrics"]["completion_tokens_per_second"] == 2.5
    assert metrics["performance_metrics"]["total_tokens_per_second"] == 1.75
    assert metrics["timing_metrics"]["load_time_ms"] == 500.0
    assert metrics["timing_metrics"]["generation_time_ms"] == 2000.0
    assert metrics["timing_metrics"]["total_time_ms"] == 4000.0
    assert metrics["timing_metrics"]["generation_ratio"] == 0.5
    assert metrics["performance_metrics"]["characters_per_token_prompt"] == 5.5
    assert metrics["performance_metrics"]["characters_per_token_completion"] == 2.2
    assert metrics["ollama_metrics"]["done"] is True
    assert metrics["ollama_metrics"]["done_reason"] == "stop"


def test_metrics_missing_ollama_values_do_not_crash_or_divide_by_zero():
    metrics = build_benchmark_metrics(
        prompt="prompt",
        response="",
        raw={
            "prompt_eval_count": 0,
            "eval_count": 0,
            "eval_duration": 0,
            "total_duration": 0,
        },
        duration_seconds=0,
    )

    assert metrics["token_metrics"]["total_tokens"] == 0
    assert metrics["performance_metrics"]["completion_tokens_per_second"] is None
    assert metrics["performance_metrics"]["total_tokens_per_second"] is None
    assert metrics["performance_metrics"]["characters_per_token_completion"] is None


def test_aggregation_summarizes_model_metrics():
    first = SimpleNamespace(
        model="m",
        task_id="a",
        run=1,
        duration_seconds=2.0,
        metrics=build_benchmark_metrics(
            prompt="one two",
            response="alpha",
            raw={
                "prompt_eval_count": 2,
                "eval_count": 3,
                "total_duration": 1_000_000_000,
            },
        ),
    )
    second = SimpleNamespace(
        model="m",
        task_id="b",
        run=1,
        duration_seconds=1.0,
        metrics=build_benchmark_metrics(
            prompt="one",
            response="alpha beta gamma",
            raw={
                "prompt_eval_count": 1,
                "eval_count": 6,
                "total_duration": 2_000_000_000,
            },
        ),
    )

    summary = aggregate_model_metrics([first, second])

    assert summary["total_prompt_tokens"] == 3
    assert summary["total_completion_tokens"] == 9
    assert summary["total_tokens"] == 12
    assert summary["fastest_task"]["task_id"] == "b"
    assert summary["slowest_task"]["task_id"] == "a"
    assert summary["longest_response"]["task_id"] == "b"


def test_metrics_csv_export(tmp_path):
    record = SimpleNamespace(
        run_id="run",
        model="qwen",
        task_id="task",
        category="coding",
        config_hash="cfg",
        metadata={"settings_hash": "settings"},
        metrics=build_benchmark_metrics(
            prompt="hello",
            response="world",
            raw={
                "prompt_eval_count": 1,
                "eval_count": 2,
                "prompt_eval_duration": 1_000_000_000,
                "eval_duration": 1_000_000_000,
                "load_duration": 100_000_000,
                "total_duration": 2_500_000_000,
            },
        ),
    )

    path = write_metrics_csv(tmp_path / "metrics.csv", [record])

    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows[0]["run_id"] == "run"
    assert rows[0]["model"] == "qwen"
    assert rows[0]["task"] == "task"
    assert rows[0]["prompt_tokens"] == "1"
    assert rows[0]["completion_tokens"] == "2"
    assert rows[0]["settings_hash"] == "settings"

