from __future__ import annotations

import csv
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


NANOSECONDS_PER_SECOND = 1_000_000_000


@dataclass(frozen=True)
class TokenMetrics:
    prompt_eval_count: int | None = None
    eval_count: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    prompt_completion_ratio: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TimingMetrics:
    prompt_eval_duration: int | None = None
    eval_duration: int | None = None
    load_duration: int | None = None
    total_duration: int | None = None
    prompt_eval_time_ms: float | None = None
    load_time_ms: float | None = None
    generation_time_ms: float | None = None
    total_time_ms: float | None = None
    generation_ratio: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PerformanceMetrics:
    prompt_tokens_per_second: float | None = None
    completion_tokens_per_second: float | None = None
    total_tokens_per_second: float | None = None
    characters_per_token_prompt: float | None = None
    characters_per_token_completion: float | None = None
    prompt_characters: int = 0
    completion_characters: int = 0
    prompt_words: int = 0
    completion_words: int = 0
    prompt_lines: int = 0
    completion_lines: int = 0
    response_size_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _number(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_div(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return round(float(numerator) / float(denominator), 6)


def _ns_to_ms(value: int | None) -> float | None:
    if value is None:
        return None
    return round(value / 1_000_000, 3)


def _ns_to_seconds(value: int | None) -> float | None:
    if value is None:
        return None
    return value / NANOSECONDS_PER_SECOND


def _word_count(text: str) -> int:
    return len([part for part in text.split() if part.strip()])


def _line_count(text: str) -> int:
    if not text:
        return 0
    return len(text.splitlines()) or 1


def build_benchmark_metrics(
    *,
    prompt: str,
    response: str,
    raw: dict[str, Any] | None,
    duration_seconds: float | None = None,
    hardware_before: dict[str, Any] | None = None,
    hardware_after: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw = raw or {}
    prompt_eval_count = _number(raw.get("prompt_eval_count"))
    eval_count = _number(raw.get("eval_count"))
    prompt_eval_duration = _number(raw.get("prompt_eval_duration"))
    eval_duration = _number(raw.get("eval_duration"))
    load_duration = _number(raw.get("load_duration"))
    total_duration = _number(raw.get("total_duration"))

    prompt_tokens = prompt_eval_count
    completion_tokens = eval_count
    total_tokens = (
        prompt_tokens + completion_tokens
        if prompt_tokens is not None and completion_tokens is not None
        else None
    )
    generation_seconds = _ns_to_seconds(eval_duration)
    prompt_eval_seconds = _ns_to_seconds(prompt_eval_duration)
    total_seconds = _ns_to_seconds(total_duration) or duration_seconds
    prompt_characters = len(prompt)
    completion_characters = len(response)

    token_metrics = TokenMetrics(
        prompt_eval_count=prompt_eval_count,
        eval_count=eval_count,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        prompt_completion_ratio=_safe_div(prompt_tokens, completion_tokens),
    )
    timing_metrics = TimingMetrics(
        prompt_eval_duration=prompt_eval_duration,
        eval_duration=eval_duration,
        load_duration=load_duration,
        total_duration=total_duration,
        prompt_eval_time_ms=_ns_to_ms(prompt_eval_duration),
        load_time_ms=_ns_to_ms(load_duration),
        generation_time_ms=_ns_to_ms(eval_duration),
        total_time_ms=_ns_to_ms(total_duration) or (
            round(duration_seconds * 1000, 3) if duration_seconds is not None else None
        ),
        generation_ratio=_safe_div(eval_duration, total_duration),
    )
    performance_metrics = PerformanceMetrics(
        prompt_tokens_per_second=_safe_div(prompt_tokens, prompt_eval_seconds),
        completion_tokens_per_second=_safe_div(completion_tokens, generation_seconds),
        total_tokens_per_second=_safe_div(total_tokens, total_seconds),
        characters_per_token_prompt=_safe_div(prompt_characters, prompt_tokens),
        characters_per_token_completion=_safe_div(completion_characters, completion_tokens),
        prompt_characters=prompt_characters,
        completion_characters=completion_characters,
        prompt_words=_word_count(prompt),
        completion_words=_word_count(response),
        prompt_lines=_line_count(prompt),
        completion_lines=_line_count(response),
        response_size_bytes=len(response.encode("utf-8")),
    )

    return {
        "token_metrics": token_metrics.to_dict(),
        "timing_metrics": timing_metrics.to_dict(),
        "performance_metrics": performance_metrics.to_dict(),
        "hardware_metrics": build_hardware_metrics(hardware_before, hardware_after),
        "ollama_metrics": {
            "prompt_eval_count": prompt_eval_count,
            "eval_count": eval_count,
            "prompt_eval_duration": prompt_eval_duration,
            "eval_duration": eval_duration,
            "load_duration": load_duration,
            "total_duration": total_duration,
            "done": raw.get("done"),
            "done_reason": raw.get("done_reason"),
            "context": raw.get("context"),
            "created_at": raw.get("created_at"),
        },
    }


def capture_hardware_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "cpu_percent": None,
        "ram_used_bytes": None,
        "ram_total_bytes": None,
        "gpu_present": None,
        "gpu_name": None,
        "vram_total_bytes": None,
        "vram_used_bytes": None,
    }
    try:
        import psutil  # type: ignore

        snapshot["cpu_percent"] = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        snapshot["ram_used_bytes"] = int(memory.used)
        snapshot["ram_total_bytes"] = int(memory.total)
    except Exception:
        pass

    snapshot.update(_gpu_snapshot())
    return snapshot


def _gpu_snapshot() -> dict[str, Any]:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        )
        first_line = result.stdout.strip().splitlines()[0]
        name, total_mb, used_mb = [part.strip() for part in first_line.split(",", 2)]
        return {
            "gpu_present": True,
            "gpu_name": name,
            "vram_total_bytes": int(float(total_mb) * 1024 * 1024),
            "vram_used_bytes": int(float(used_mb) * 1024 * 1024),
        }
    except Exception:
        return {
            "gpu_present": None,
            "gpu_name": None,
            "vram_total_bytes": None,
            "vram_used_bytes": None,
        }


def build_hardware_metrics(
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> dict[str, Any]:
    before = before or {}
    after = after or {}
    ram_values = [
        value
        for value in [before.get("ram_used_bytes"), after.get("ram_used_bytes")]
        if value is not None
    ]
    return {
        "cpu_percent_before": before.get("cpu_percent"),
        "cpu_percent_after": after.get("cpu_percent"),
        "ram_used_bytes_before": before.get("ram_used_bytes"),
        "ram_used_bytes_after": after.get("ram_used_bytes"),
        "ram_total_bytes": after.get("ram_total_bytes") or before.get("ram_total_bytes"),
        "peak_ram_used_bytes": max(ram_values) if ram_values else None,
        "gpu_present": after.get("gpu_present") if after.get("gpu_present") is not None else before.get("gpu_present"),
        "gpu_name": after.get("gpu_name") or before.get("gpu_name"),
        "vram_total_bytes": after.get("vram_total_bytes") or before.get("vram_total_bytes"),
        "vram_used_bytes_before": before.get("vram_used_bytes"),
        "vram_used_bytes_after": after.get("vram_used_bytes"),
    }


def extract_model_capability_metadata(model_metadata: dict[str, Any]) -> dict[str, Any]:
    raw = model_metadata.get("raw") or {}
    details = model_metadata.get("details") or raw.get("details") or {}
    model_info = model_metadata.get("model_info") or raw.get("model_info") or {}
    return {
        "gguf_format": details.get("format") or raw.get("format") or model_info.get("general.file_type"),
        "quantization": details.get("quantization_level") or details.get("quantization"),
        "parameter_size": details.get("parameter_size") or model_info.get("general.parameter_count"),
        "context_length": (
            details.get("context_length")
            or raw.get("context_length")
            or model_info.get("llama.context_length")
            or model_info.get("qwen2.context_length")
        ),
        "embedding_length": (
            details.get("embedding_length")
            or raw.get("embedding_length")
            or model_info.get("llama.embedding_length")
            or model_info.get("qwen2.embedding_length")
        ),
        "capabilities": (
            model_metadata.get("capabilities")
            or raw.get("capabilities")
            or details.get("capabilities")
        ),
        "parameters": model_metadata.get("parameters") or raw.get("parameters"),
    }


def aggregate_model_metrics(records: list[Any]) -> dict[str, Any]:
    prompt_tokens = [_metric(record, "token_metrics", "prompt_tokens") for record in records]
    completion_tokens = [_metric(record, "token_metrics", "completion_tokens") for record in records]
    total_tokens = [_metric(record, "token_metrics", "total_tokens") for record in records]
    tps_values = [_metric(record, "performance_metrics", "total_tokens_per_second") for record in records]
    prompt_chars = [_metric(record, "performance_metrics", "prompt_characters") for record in records]
    response_chars = [_metric(record, "performance_metrics", "completion_characters") for record in records]
    sorted_by_duration = sorted(records, key=lambda record: record.duration_seconds)
    sorted_by_response = sorted(
        records,
        key=lambda record: _metric(record, "performance_metrics", "completion_characters") or 0,
    )
    return {
        "total_prompt_tokens": _sum(prompt_tokens),
        "total_completion_tokens": _sum(completion_tokens),
        "total_tokens": _sum(total_tokens),
        "average_tokens_per_second": _average(tps_values),
        "average_prompt_size": _average(prompt_chars),
        "average_response_size": _average(response_chars),
        "slowest_task": _task_ref(sorted_by_duration[-1]) if sorted_by_duration else None,
        "fastest_task": _task_ref(sorted_by_duration[0]) if sorted_by_duration else None,
        "longest_response": _task_ref(sorted_by_response[-1]) if sorted_by_response else None,
        "shortest_response": _task_ref(sorted_by_response[0]) if sorted_by_response else None,
    }


def aggregate_run_metrics(records: list[Any]) -> dict[str, Any]:
    total_tokens = [_metric(record, "token_metrics", "total_tokens") for record in records]
    response_chars = [_metric(record, "performance_metrics", "completion_characters") for record in records]
    token_rates = [_metric(record, "performance_metrics", "total_tokens_per_second") for record in records]
    return {
        "total_tokens": _sum(total_tokens),
        "total_duration_seconds": round(sum(record.duration_seconds for record in records), 3),
        "average_response_size": _average(response_chars),
        "average_token_rate": _average(token_rates),
    }


def write_metrics_csv(path: str | Path, records: list[Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "run_id",
        "model",
        "task",
        "category",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "prompt_tps",
        "completion_tps",
        "duration_ms",
        "load_ms",
        "generation_ms",
        "response_chars",
        "response_words",
        "response_lines",
        "settings_hash",
        "config_hash",
    ]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "run_id": record.run_id,
                    "model": record.model,
                    "task": record.task_id,
                    "category": record.category,
                    "prompt_tokens": _metric(record, "token_metrics", "prompt_tokens"),
                    "completion_tokens": _metric(record, "token_metrics", "completion_tokens"),
                    "total_tokens": _metric(record, "token_metrics", "total_tokens"),
                    "prompt_tps": _metric(record, "performance_metrics", "prompt_tokens_per_second"),
                    "completion_tps": _metric(record, "performance_metrics", "completion_tokens_per_second"),
                    "duration_ms": _metric(record, "timing_metrics", "total_time_ms"),
                    "load_ms": _metric(record, "timing_metrics", "load_time_ms"),
                    "generation_ms": _metric(record, "timing_metrics", "generation_time_ms"),
                    "response_chars": _metric(record, "performance_metrics", "completion_characters"),
                    "response_words": _metric(record, "performance_metrics", "completion_words"),
                    "response_lines": _metric(record, "performance_metrics", "completion_lines"),
                    "settings_hash": record.metadata.get("settings_hash"),
                    "config_hash": record.config_hash,
                }
            )
    return output


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def _metric(record: Any, group: str, key: str) -> Any:
    metrics = getattr(record, "metrics", None) or {}
    values = metrics.get(group) or {}
    return values.get(key)


def _sum(values: list[Any]) -> int | None:
    usable = [value for value in values if value is not None]
    if not usable:
        return None
    return int(sum(usable))


def _average(values: list[Any]) -> float | None:
    usable = [float(value) for value in values if value is not None]
    if not usable:
        return None
    return round(sum(usable) / len(usable), 6)


def _task_ref(record: Any) -> dict[str, Any]:
    return {
        "model": record.model,
        "task_id": record.task_id,
        "run": record.run,
        "duration_seconds": record.duration_seconds,
    }
