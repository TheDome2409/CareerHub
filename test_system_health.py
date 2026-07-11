from types import SimpleNamespace

from careerhub.benchmark_models import BenchmarkConfig, BenchmarkModel, BenchmarkSettings, BenchmarkTask
from careerhub.benchmark_runner import run_benchmark
from careerhub.ollama_client import OllamaGenerateResult
from careerhub.system_health import (
    SystemHealthMonitor,
    SystemHealthSnapshot,
    capture_snapshot,
    summarize_run_health,
)


class FakePsutil:
    @staticmethod
    def cpu_percent(interval=None):
        return 42.0

    @staticmethod
    def cpu_freq():
        return SimpleNamespace(current=3200.0, max=4800.0)

    @staticmethod
    def cpu_count(logical=True):
        return 16 if logical else 8

    @staticmethod
    def virtual_memory():
        return SimpleNamespace(total=1000, available=100, used=900, percent=90.0)

    @staticmethod
    def swap_memory():
        return SimpleNamespace(total=100, used=10, percent=10.0)

    @staticmethod
    def disk_partitions(all=False):
        return [SimpleNamespace(mountpoint="C:\\", device="C:")]

    @staticmethod
    def disk_usage(mountpoint):
        return SimpleNamespace(total=1000, used=950, free=50, percent=95.0)

    @staticmethod
    def disk_io_counters():
        return SimpleNamespace(read_bytes=1, write_bytes=2, read_count=3, write_count=4)

    @staticmethod
    def net_io_counters():
        return SimpleNamespace(bytes_sent=1, bytes_recv=2, packets_sent=3, packets_recv=4)

    @staticmethod
    def process_iter(attrs):
        info = {
            "pid": 1,
            "name": "python",
            "username": "user",
            "cpu_percent": 10.0,
            "memory_percent": 5.0,
            "memory_info": SimpleNamespace(rss=123),
            "cmdline": ["python", "script.py"],
        }
        return [SimpleNamespace(info=info)]


class FakeOllamaClient:
    def generate(self, *, model, prompt, keep_alive, options):
        return OllamaGenerateResult(
            response="ok",
            duration_seconds=0.1,
            error=None,
            raw={"prompt_eval_count": 1, "eval_count": 1, "total_duration": 100_000_000},
        )

    def get_model_metadata(self, model_name):
        return {"name": model_name, "tag": "1", "digest": None, "details": {}, "raw": {}}

    def get_ollama_version(self):
        return None


def test_snapshot_with_mocked_psutil(monkeypatch):
    import careerhub.system_health as system_health

    monkeypatch.setattr(system_health, "psutil", FakePsutil)
    monkeypatch.setattr(system_health, "capture_gpu_summary_best_effort", lambda: {"provider": None, "devices": []})

    snapshot = capture_snapshot("test")

    assert snapshot.label == "test"
    assert snapshot.cpu["percent"] == 42.0
    assert snapshot.memory["percent"] == 90.0
    assert snapshot.top_processes["by_memory"][0]["name"] == "python"


def test_snapshot_fallback_without_psutil(monkeypatch):
    import careerhub.system_health as system_health

    monkeypatch.setattr(system_health, "psutil", None)
    snapshot = capture_snapshot("fallback")

    assert snapshot.memory["percent"] is None
    assert "psutil_not_available" in snapshot.warnings


def test_summary_detects_memory_swap_cpu_and_disk_warnings():
    start = SystemHealthSnapshot(
        created_at="now",
        label="start",
        cpu={"percent": 10},
        memory={"percent": 50, "available_bytes": 500},
        swap={"percent": 0},
        disk=[{"percent": 50}],
        top_processes={"by_memory": [], "by_cpu": []},
        gpu={"provider": None, "devices": []},
    )
    sample = SystemHealthSnapshot(
        created_at="now",
        label="sample",
        cpu={"percent": 95},
        memory={"percent": 97, "available_bytes": 50},
        swap={"percent": 3},
        disk=[{"percent": 95}],
        top_processes={"by_memory": [{"pid": 1, "rss_bytes": 100}], "by_cpu": [{"pid": 1, "cpu_percent": 95}]},
        gpu={"provider": None, "devices": []},
    )
    summary = summarize_run_health(start, start, [sample])

    assert summary["peak_memory_percent"] == 97.0
    assert summary["min_available_memory_bytes"] == 50
    assert "memory_above_90_percent" in summary["warnings"]
    assert "swap_used" in summary["warnings"]
    assert "high_background_cpu" in summary["warnings"]
    assert "disk_low_free_space" in summary["warnings"]
    assert "gpu_metrics_unavailable" in summary["warnings"]


def test_system_health_output_files_are_written(tmp_path, monkeypatch):
    import careerhub.system_health as system_health

    monkeypatch.setattr(system_health, "psutil", None)
    monitor = SystemHealthMonitor(tmp_path)
    start = monitor.capture_snapshot("start")
    end = monitor.capture_snapshot("end")
    monitor.capture_sample("sample")

    start_path = monitor.write_snapshot("system_health_start.json", start)
    end_path = monitor.write_snapshot("system_health_end.json", end)
    samples_path = monitor.write_samples()
    summary_path, summary = monitor.write_summary(start, end)

    assert start_path.exists()
    assert end_path.exists()
    assert samples_path.exists()
    assert summary_path.exists()
    assert "psutil_not_available" in summary["warnings"]


def test_runner_writes_system_health_files(tmp_path, monkeypatch):
    import careerhub.system_health as system_health

    monkeypatch.setattr(system_health, "psutil", None)
    config = BenchmarkConfig(
        models=[BenchmarkModel(name="health-model:1", runs=1)],
        settings=BenchmarkSettings(),
    )
    task = BenchmarkTask(
        id="health_task",
        category="coding",
        title="Health Task",
        prompt="Prompt",
        expected_output_type="text",
    )

    summary = run_benchmark(
        config=config,
        tasks=[task],
        client=FakeOllamaClient(),
        output_dir=tmp_path / "outputs",
        report_dir=tmp_path / "reports",
        run_id="health_run",
        no_archive=True,
        health_monitor=True,
        health_interval_seconds=1,
    )

    assert (summary.output_root / "system_health_start.json").exists()
    assert (summary.output_root / "system_health_end.json").exists()
    assert (summary.output_root / "system_health_samples.json").exists()
    assert (summary.output_root / "system_health_summary.json").exists()
    assert summary.run_metadata.system_health["warnings"]
