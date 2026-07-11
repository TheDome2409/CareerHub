from __future__ import annotations

import json
import shutil
import subprocess
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from careerhub.benchmark_metadata import utc_now_iso

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - depends on local optional dependency.
    psutil = None


@dataclass
class SystemHealthSnapshot:
    created_at: str
    label: str
    cpu: dict[str, Any] = field(default_factory=dict)
    memory: dict[str, Any] = field(default_factory=dict)
    swap: dict[str, Any] = field(default_factory=dict)
    disk: list[dict[str, Any]] = field(default_factory=list)
    io: dict[str, Any] = field(default_factory=dict)
    network: dict[str, Any] = field(default_factory=dict)
    top_processes: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    gpu: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SystemHealthMonitor:
    def __init__(
        self,
        output_dir: str | Path,
        interval_seconds: int = 30,
        enabled: bool = False,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.interval_seconds = max(1, int(interval_seconds))
        self.enabled = enabled
        self.samples: list[SystemHealthSnapshot] = []
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def capture_snapshot(self, label: str) -> SystemHealthSnapshot:
        return capture_snapshot(label, detailed=self.enabled)

    def capture_sample(self, label: str) -> SystemHealthSnapshot:
        snapshot = self.capture_snapshot(label)
        self.samples.append(snapshot)
        return snapshot

    def start_periodic(self) -> None:
        if not self.enabled or self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._periodic_loop, daemon=True)
        self._thread.start()

    def stop_periodic(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def _periodic_loop(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            self.capture_sample("periodic")

    def write_snapshot(self, filename: str, snapshot: SystemHealthSnapshot) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / filename
        path.write_text(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def write_samples(self, filename: str = "system_health_samples.json") -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / filename
        payload = [sample.to_dict() for sample in self.samples]
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def write_summary(
        self,
        start: SystemHealthSnapshot,
        end: SystemHealthSnapshot,
        filename: str = "system_health_summary.json",
    ) -> tuple[Path, dict[str, Any]]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / filename
        summary = summarize_run_health(start, end, self.samples)
        path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return path, summary


def capture_snapshot(label: str, detailed: bool = True) -> SystemHealthSnapshot:
    warnings = []
    if psutil is None:
        warnings.append("psutil_not_available")
    return SystemHealthSnapshot(
        created_at=utc_now_iso(),
        label=label,
        cpu=_cpu_summary(),
        memory=_memory_summary(),
        swap=_swap_summary(),
        disk=capture_storage_summary(),
        io=_io_summary(),
        network=capture_network_summary_best_effort(),
        top_processes=capture_process_summary() if detailed else {"by_memory": [], "by_cpu": []},
        gpu=capture_gpu_summary_best_effort() if detailed else {"provider": None, "devices": []},
        warnings=warnings,
    )


def capture_process_summary() -> dict[str, list[dict[str, Any]]]:
    if psutil is None:
        return {"by_memory": [], "by_cpu": []}
    processes = []
    for process in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent", "memory_info", "cmdline"]):
        try:
            info = process.info
            cmdline = " ".join(info.get("cmdline") or [])
            processes.append(
                {
                    "pid": info.get("pid"),
                    "name": info.get("name"),
                    "username": info.get("username"),
                    "cpu_percent": info.get("cpu_percent"),
                    "memory_percent": info.get("memory_percent"),
                    "rss_bytes": getattr(info.get("memory_info"), "rss", None),
                    "cmdline": cmdline[:240] if cmdline else None,
                }
            )
        except Exception:
            continue
    by_memory = sorted(processes, key=lambda item: item.get("rss_bytes") or 0, reverse=True)[:10]
    by_cpu = sorted(processes, key=lambda item: item.get("cpu_percent") or 0, reverse=True)[:10]
    return {"by_memory": by_memory, "by_cpu": by_cpu}


def capture_gpu_summary_best_effort() -> dict[str, Any]:
    nvidia = _nvidia_smi()
    if nvidia["devices"]:
        return nvidia
    rocm = _rocm_smi()
    if rocm["devices"]:
        return rocm
    return {"provider": None, "devices": []}


def capture_storage_summary() -> list[dict[str, Any]]:
    if psutil is None:
        return []
    result = []
    for partition in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            result.append(
                {
                    "mountpoint": partition.mountpoint,
                    "device": partition.device,
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "percent": usage.percent,
                }
            )
        except Exception:
            continue
    return result


def capture_network_summary_best_effort() -> dict[str, Any]:
    if psutil is None:
        return {"bytes_sent": None, "bytes_recv": None, "packets_sent": None, "packets_recv": None}
    try:
        counters = psutil.net_io_counters()
        return {
            "bytes_sent": counters.bytes_sent,
            "bytes_recv": counters.bytes_recv,
            "packets_sent": counters.packets_sent,
            "packets_recv": counters.packets_recv,
        }
    except Exception:
        return {"bytes_sent": None, "bytes_recv": None, "packets_sent": None, "packets_recv": None}


def summarize_run_health(
    start: SystemHealthSnapshot,
    end: SystemHealthSnapshot,
    samples: list[SystemHealthSnapshot],
) -> dict[str, Any]:
    all_snapshots = [start, *samples, end]
    memory_percents = [_path(snapshot, "memory", "percent") for snapshot in all_snapshots]
    available_memory = [_path(snapshot, "memory", "available_bytes") for snapshot in all_snapshots]
    cpu_percents = [_path(snapshot, "cpu", "percent") for snapshot in all_snapshots]
    swap_percents = [_path(snapshot, "swap", "percent") for snapshot in all_snapshots]
    disk_free_percents = []
    for snapshot in all_snapshots:
        for disk in snapshot.disk:
            percent = disk.get("percent")
            if percent is not None:
                disk_free_percents.append(100 - float(percent))

    warnings = []
    peak_memory = _max(memory_percents)
    peak_cpu = _max(cpu_percents)
    peak_swap = _max(swap_percents)
    min_disk_free = _min(disk_free_percents)
    if peak_memory is not None and peak_memory >= 90:
        warnings.append("memory_above_90_percent")
    if peak_swap is not None and peak_swap > 0:
        warnings.append("swap_used")
    if peak_cpu is not None and peak_cpu >= 85:
        warnings.append("high_background_cpu")
    if min_disk_free is not None and min_disk_free <= 10:
        warnings.append("disk_low_free_space")
    if not any(snapshot.gpu.get("devices") for snapshot in all_snapshots):
        warnings.append("gpu_metrics_unavailable")
    for snapshot in all_snapshots:
        warnings.extend(snapshot.warnings)

    return {
        "peak_memory_percent": peak_memory,
        "min_available_memory_bytes": _min(available_memory),
        "peak_cpu_percent": peak_cpu,
        "peak_swap_percent": peak_swap,
        "disk_free_min_percent": min_disk_free,
        "top_memory_processes_over_run": _top_processes(all_snapshots, "by_memory"),
        "top_cpu_processes_over_run": _top_processes(all_snapshots, "by_cpu"),
        "warnings": sorted(set(warnings)),
    }


def _cpu_summary() -> dict[str, Any]:
    if psutil is None:
        return {
            "percent": None,
            "load_avg": None,
            "frequency_current_mhz": None,
            "frequency_max_mhz": None,
            "physical_cores": None,
            "logical_cores": None,
        }
    try:
        frequency = psutil.cpu_freq()
    except Exception:
        frequency = None
    return {
        "percent": _safe_call(lambda: psutil.cpu_percent(interval=None)),
        "load_avg": _safe_call(lambda: list(psutil.getloadavg())) if hasattr(psutil, "getloadavg") else None,
        "frequency_current_mhz": getattr(frequency, "current", None),
        "frequency_max_mhz": getattr(frequency, "max", None),
        "physical_cores": _safe_call(lambda: psutil.cpu_count(logical=False)),
        "logical_cores": _safe_call(lambda: psutil.cpu_count(logical=True)),
    }


def _memory_summary() -> dict[str, Any]:
    if psutil is None:
        return {"total_bytes": None, "available_bytes": None, "used_bytes": None, "percent": None}
    try:
        memory = psutil.virtual_memory()
        return {
            "total_bytes": memory.total,
            "available_bytes": memory.available,
            "used_bytes": memory.used,
            "percent": memory.percent,
        }
    except Exception:
        return {"total_bytes": None, "available_bytes": None, "used_bytes": None, "percent": None}


def _swap_summary() -> dict[str, Any]:
    if psutil is None:
        return {"total_bytes": None, "used_bytes": None, "percent": None}
    try:
        swap = psutil.swap_memory()
        return {"total_bytes": swap.total, "used_bytes": swap.used, "percent": swap.percent}
    except Exception:
        return {"total_bytes": None, "used_bytes": None, "percent": None}


def _io_summary() -> dict[str, Any]:
    if psutil is None:
        return {"read_bytes": None, "write_bytes": None, "read_count": None, "write_count": None}
    try:
        counters = psutil.disk_io_counters()
        return {
            "read_bytes": counters.read_bytes,
            "write_bytes": counters.write_bytes,
            "read_count": counters.read_count,
            "write_count": counters.write_count,
        }
    except Exception:
        return {"read_bytes": None, "write_bytes": None, "read_count": None, "write_count": None}


def _nvidia_smi() -> dict[str, Any]:
    if shutil.which("nvidia-smi") is None:
        return {"provider": "nvidia-smi", "devices": []}
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        )
        devices = []
        for line in result.stdout.strip().splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) < 6:
                continue
            devices.append(
                {
                    "name": parts[0],
                    "utilization_percent": _float_or_none(parts[1]),
                    "memory_used_bytes": _mb_to_bytes(parts[2]),
                    "memory_total_bytes": _mb_to_bytes(parts[3]),
                    "temperature_c": _float_or_none(parts[4]),
                    "driver_version": parts[5],
                }
            )
        return {"provider": "nvidia-smi", "devices": devices}
    except Exception:
        return {"provider": "nvidia-smi", "devices": []}


def _rocm_smi() -> dict[str, Any]:
    if shutil.which("rocm-smi") is None:
        return {"provider": "rocm-smi", "devices": []}
    try:
        result = subprocess.run(["rocm-smi", "--showproductname"], capture_output=True, text=True, timeout=3, check=True)
        devices = []
        for line in result.stdout.splitlines():
            if "GPU" in line and ":" in line:
                devices.append(
                    {
                        "name": line.split(":", 1)[-1].strip(),
                        "utilization_percent": None,
                        "memory_used_bytes": None,
                        "memory_total_bytes": None,
                        "temperature_c": None,
                        "driver_version": None,
                    }
                )
        return {"provider": "rocm-smi", "devices": devices}
    except Exception:
        return {"provider": "rocm-smi", "devices": []}


def _top_processes(snapshots: list[SystemHealthSnapshot], key: str) -> list[dict[str, Any]]:
    seen = {}
    for snapshot in snapshots:
        for process in snapshot.top_processes.get(key, []):
            pid = process.get("pid")
            current = seen.get(pid)
            value_key = "rss_bytes" if key == "by_memory" else "cpu_percent"
            if current is None or (process.get(value_key) or 0) > (current.get(value_key) or 0):
                seen[pid] = process
    value_key = "rss_bytes" if key == "by_memory" else "cpu_percent"
    return sorted(seen.values(), key=lambda item: item.get(value_key) or 0, reverse=True)[:10]


def _path(snapshot: SystemHealthSnapshot, group: str, key: str) -> Any:
    return getattr(snapshot, group, {}).get(key)


def _max(values: list[Any]) -> float | None:
    usable = [float(value) for value in values if value is not None]
    return max(usable) if usable else None


def _min(values: list[Any]) -> float | int | None:
    usable = [value for value in values if value is not None]
    return min(usable) if usable else None


def _safe_call(callback):
    try:
        return callback()
    except Exception:
        return None


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mb_to_bytes(value: Any) -> int | None:
    number = _float_or_none(value)
    if number is None:
        return None
    return int(number * 1024 * 1024)
