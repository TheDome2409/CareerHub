from __future__ import annotations

import argparse
import json
import logging
import platform
import sys
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from careerhub.benchmark_archive import BenchmarkArchive, DEFAULT_ARCHIVE_DB
from careerhub.benchmark_metadata import (
    BenchmarkRunMetadata,
    careerhub_version,
    git_metadata,
    hardware_summary,
    make_run_id,
    stable_json_hash,
    utc_now_iso,
)
from careerhub.benchmark_metrics import (
    aggregate_model_metrics,
    aggregate_run_metrics,
    build_benchmark_metrics,
    capture_hardware_snapshot,
    extract_model_capability_metadata,
    write_json,
    write_metrics_csv,
)
from careerhub.benchmark_models import (
    BenchmarkConfig,
    BenchmarkModel,
    BenchmarkTask,
    BenchmarkTaskSet,
    load_benchmark_config,
    load_benchmark_task_set,
    safe_model_name,
)
from careerhub.benchmark_progress import BenchmarkProgressTracker
from careerhub.ollama_client import OllamaGenerateClient
from careerhub.system_health import SystemHealthMonitor


logger = logging.getLogger(__name__)


@dataclass
class BenchmarkRecord:
    run_id: str
    model: str
    model_digest: str | None
    task_id: str
    category: str
    run: int
    prompt: str
    response: str
    duration_seconds: float
    created_at: str
    error: str | None
    task_version: str
    prompt_version: str
    task_hash: str
    prompt_hash: str
    config_hash: str
    benchmark_suite_version: str
    careerhub_version: str
    git_commit_hash: str | None
    git_dirty_state: str
    metrics: dict
    metadata: dict
    output_path: Path | None = None


@dataclass
class BenchmarkRunSummary:
    run_id: str
    output_root: Path
    report_path: Path | None
    run_metadata: BenchmarkRunMetadata | None
    records: list[BenchmarkRecord] = field(default_factory=list)
    model_order: list[str] = field(default_factory=list)
    progress_summary: dict | None = None


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _created_at() -> str:
    return utc_now_iso()


def filter_models(
    models: list[BenchmarkModel],
    selected_models: Iterable[str] | None,
    runs_override: int | None,
) -> list[BenchmarkModel]:
    selected = set(selected_models or [])
    result = []
    for model in models:
        if selected and model.name not in selected:
            continue
        result.append(
            BenchmarkModel(
                name=model.name,
                runs=runs_override if runs_override is not None else model.runs,
                keep_alive=model.keep_alive,
            )
        )
    return result


def filter_tasks(
    tasks: list[BenchmarkTask],
    selected_categories: Iterable[str] | None,
) -> list[BenchmarkTask]:
    categories = {value.strip() for value in selected_categories or [] if value.strip()}
    if not categories:
        return tasks
    return [task for task in tasks if task.category in categories]


def _settings_dict(config: BenchmarkConfig) -> dict:
    return {
        "temperature": config.settings.temperature,
        "top_p": config.settings.top_p,
        "num_ctx": config.settings.num_ctx,
        "timeout_seconds": config.settings.timeout_seconds,
    }


def _config_hash(config: BenchmarkConfig) -> str:
    if config.config_hash:
        return config.config_hash
    return stable_json_hash(
        {
            "models": [model.__dict__ for model in config.models],
            "settings": {
                **_settings_dict(config),
                "tasks_path": str(config.settings.tasks_path),
            },
        }
    )


def _client_model_metadata(client, model_name: str) -> dict:
    if hasattr(client, "get_model_metadata"):
        return client.get_model_metadata(model_name)
    return {
        "name": model_name,
        "tag": model_name.rsplit(":", 1)[-1] if ":" in model_name else None,
        "digest": None,
        "details": {},
        "raw": {},
    }


def _client_ollama_version(client) -> str | None:
    if hasattr(client, "get_ollama_version"):
        return client.get_ollama_version()
    return None


def _build_run_metadata(
    *,
    run_id: str,
    run_label: str | None,
    config: BenchmarkConfig,
    task_set: BenchmarkTaskSet,
    suite_version_override: str | None,
    prompt_version_override: str | None,
    task_version_override: str | None,
    ollama_version: str | None,
    system_health: dict | None = None,
) -> BenchmarkRunMetadata:
    git = git_metadata(Path("."))
    return BenchmarkRunMetadata(
        run_id=run_id,
        run_label=run_label,
        created_at=_created_at(),
        careerhub_version=careerhub_version(),
        git_commit_hash=git.commit_hash,
        git_branch=git.branch,
        git_dirty_state=git.dirty_state,
        benchmark_suite_version=suite_version_override or task_set.suite_version,
        task_set_version=task_version_override or task_set.task_set_version,
        prompt_set_version=prompt_version_override or task_set.prompt_set_version,
        config_hash=_config_hash(config),
        task_file_hash=task_set.task_file_hash,
        ollama_version=ollama_version,
        python_version=sys.version.replace("\n", " "),
        platform=platform.platform(),
        hardware_summary=hardware_summary(),
        settings=_settings_dict(config),
        system_health=system_health,
    )


def _task_items(
    tasks: list[BenchmarkTask] | BenchmarkTaskSet,
    *,
    prompt_version_override: str | None,
    task_version_override: str | None,
) -> tuple[BenchmarkTaskSet, list[BenchmarkTask]]:
    task_set = tasks if isinstance(tasks, BenchmarkTaskSet) else BenchmarkTaskSet(tasks=tasks)
    items = [
        BenchmarkTask(
            id=task.id,
            category=task.category,
            title=task.title,
            prompt=task.prompt,
            expected_output_type=task.expected_output_type,
            task_version=task_version_override or task.task_version,
            prompt_version=prompt_version_override or task.prompt_version,
            evaluation_hints=task.evaluation_hints,
        )
        for task in task_set.tasks
    ]
    return task_set, items


def write_output_record(
    output_root: Path,
    record: BenchmarkRecord,
) -> Path:
    model_dir = output_root / safe_model_name(record.model)
    model_dir.mkdir(parents=True, exist_ok=True)
    output_path = model_dir / f"{record.task_id}_run_{record.run}.json"
    payload = {
        "run_id": record.run_id,
        "model": record.model,
        "model_digest": record.model_digest,
        "task_id": record.task_id,
        "category": record.category,
        "run": record.run,
        "task_version": record.task_version,
        "prompt_version": record.prompt_version,
        "task_hash": record.task_hash,
        "prompt_hash": record.prompt_hash,
        "config_hash": record.config_hash,
        "benchmark_suite_version": record.benchmark_suite_version,
        "careerhub_version": record.careerhub_version,
        "git_commit_hash": record.git_commit_hash,
        "git_dirty_state": record.git_dirty_state,
        "prompt": record.prompt,
        "response": record.response,
        "duration_seconds": round(record.duration_seconds, 3),
        "created_at": record.created_at,
        "error": record.error,
        "metrics": record.metrics,
        "metadata": record.metadata,
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    record.output_path = output_path
    return output_path


def _record_from_existing(
    output_path: Path,
    *,
    task: BenchmarkTask,
    model_name: str,
    run_id: str,
    run_metadata: BenchmarkRunMetadata,
    model_digest: str | None,
) -> BenchmarkRecord:
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    return BenchmarkRecord(
        run_id=run_id,
        model=str(payload.get("model", model_name)),
        model_digest=payload.get("model_digest", model_digest),
        task_id=str(payload.get("task_id", task.id)),
        category=str(payload.get("category", task.category)),
        run=int(payload.get("run", 1)),
        prompt=str(payload.get("prompt", task.prompt)),
        response=str(payload.get("response", "")),
        duration_seconds=float(payload.get("duration_seconds", 0)),
        created_at=str(payload.get("created_at", _created_at())),
        error=payload.get("error"),
        task_version=str(payload.get("task_version", task.task_version)),
        prompt_version=str(payload.get("prompt_version", task.prompt_version)),
        task_hash=str(payload.get("task_hash", task.task_hash)),
        prompt_hash=str(payload.get("prompt_hash", task.prompt_hash)),
        config_hash=str(payload.get("config_hash", run_metadata.config_hash)),
        benchmark_suite_version=str(
            payload.get("benchmark_suite_version", run_metadata.benchmark_suite_version)
        ),
        careerhub_version=str(payload.get("careerhub_version", run_metadata.careerhub_version)),
        git_commit_hash=payload.get("git_commit_hash", run_metadata.git_commit_hash),
        git_dirty_state=str(payload.get("git_dirty_state", run_metadata.git_dirty_state)),
        metrics=payload.get("metrics") or {},
        metadata={**(payload.get("metadata") or {}), "resumed": True},
        output_path=output_path,
    )


def _write_run_metadata(output_root: Path, run_metadata: BenchmarkRunMetadata) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "run_metadata.json").write_text(
        json.dumps(run_metadata.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_model_metadata(
    output_root: Path,
    model_name: str,
    model_metadata: dict,
    model_settings: dict,
) -> None:
    model_dir = output_root / safe_model_name(model_name)
    model_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "model_name": model_name,
        "model_tag": model_metadata.get("tag"),
        "model_digest": model_metadata.get("digest"),
        "model_details": model_metadata.get("details") or {},
        "capability_metadata": extract_model_capability_metadata(model_metadata),
        "raw": model_metadata.get("raw") or {},
        "settings": model_settings,
        "settings_hash": stable_json_hash(model_settings),
    }
    (model_dir / "model_metadata.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def generate_report(
    *,
    run_id: str,
    run_label: str | None,
    report_dir: Path,
    output_root: Path,
    models: list[BenchmarkModel],
    tasks: list[BenchmarkTask],
    records: list[BenchmarkRecord],
    run_metadata: BenchmarkRunMetadata,
    model_metadata_by_name: dict[str, dict],
    progress_summary: dict | None = None,
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{run_id}_summary.md"
    successful = [record for record in records if not record.error]
    failed = [record for record in records if record.error]
    run_metrics = aggregate_run_metrics(records)
    durations_by_model: dict[str, list[float]] = {}
    for record in records:
        durations_by_model.setdefault(record.model, []).append(record.duration_seconds)

    sorted_records = sorted(records, key=lambda item: item.duration_seconds)
    fastest = sorted_records[0] if sorted_records else None
    slowest = sorted_records[-1] if sorted_records else None

    lines = [
        "# CareerHub LLM Benchmark Summary",
        "",
        f"Run ID: `{run_id}`",
        f"Run Label: `{run_label or ''}`",
        f"Created: `{run_metadata.created_at}`",
        f"Outputs: `{output_root}`",
        f"Run Summary: `{output_root / 'run_summary.json'}`",
        f"Metrics CSV: `{report_dir / f'{run_id}_metrics.csv'}`",
        f"Git Commit: `{run_metadata.git_commit_hash}`",
        f"Git Branch: `{run_metadata.git_branch}`",
        f"Dirty State: `{run_metadata.git_dirty_state}`",
        f"Benchmark Suite Version: `{run_metadata.benchmark_suite_version}`",
        f"Task Set Version: `{run_metadata.task_set_version}`",
        f"Prompt Set Version: `{run_metadata.prompt_set_version}`",
        f"Config Hash: `{run_metadata.config_hash}`",
        f"Ollama Version: `{run_metadata.ollama_version}`",
        "",
        "## System Health",
    ]
    health = run_metadata.system_health or {}
    health_summary = health.get("summary") or {}
    lines.extend(
        [
            f"- Peak RAM: {health_summary.get('peak_memory_percent')}",
            f"- Minimum available RAM: {health_summary.get('min_available_memory_bytes')}",
            f"- Peak CPU: {health_summary.get('peak_cpu_percent')}",
            f"- Peak Swap: {health_summary.get('peak_swap_percent')}",
            f"- Warnungen: {', '.join(health.get('warnings') or []) or '-'}",
            "",
            "## Modelle",
        ]
    )
    for model in models:
        model_meta = model_metadata_by_name.get(model.name, {})
        lines.append(
            f"- `{model.name}`: runs={model.runs}, keep_alive={model.keep_alive}, "
            f"digest=`{model_meta.get('digest')}`"
        )

    lines.extend(
        [
            "",
            "## Einstellungen",
            f"- temperature: {run_metadata.settings.get('temperature')}",
            f"- top_p: {run_metadata.settings.get('top_p')}",
            f"- num_ctx: {run_metadata.settings.get('num_ctx')}",
            f"- timeout_seconds: {run_metadata.settings.get('timeout_seconds')}",
            "",
            "## Ergebnis",
            f"- Tasks: {len(tasks)}",
            f"- Läufe gesamt: {len(records)}",
            f"- Erfolgreich: {len(successful)}",
            f"- Fehler: {len(failed)}",
            f"- Gesamte Tokens: {run_metrics.get('total_tokens')}",
            f"- Gesamte Laufzeit: {run_metrics.get('total_duration_seconds')}s",
            f"- Durchschnittliche Antwortgröße: {run_metrics.get('average_response_size')}",
            f"- Durchschnittliche Tokenrate: {run_metrics.get('average_token_rate')}",
            "",
            "## Progress Summary",
            f"- started_at: {progress_summary.get('started_at') if progress_summary else None}",
            f"- finished_at: {progress_summary.get('finished_at') if progress_summary else None}",
            f"- total duration: {progress_summary.get('total_duration_seconds') if progress_summary else None}s",
            f"- completed task runs: {progress_summary.get('completed_task_runs') if progress_summary else None}",
            f"- failed task runs: {progress_summary.get('failed_task_runs') if progress_summary else None}",
            f"- average task duration: {progress_summary.get('average_task_duration_seconds') if progress_summary else None}s",
            f"- slowest task: {progress_summary.get('slowest_task') if progress_summary else None}",
            f"- fastest task: {progress_summary.get('fastest_task') if progress_summary else None}",
            "",
            "## Durchschnittliche Laufzeit pro Modell",
        ]
    )
    for model, durations in durations_by_model.items():
        average = sum(durations) / len(durations)
        lines.append(f"- `{model}`: {average:.2f}s")

    lines.extend(["", "## Schnellste / langsamste Aufgabe"])
    if fastest:
        lines.append(
            f"- Schnellste: `{fastest.model}` / `{fastest.task_id}` / "
            f"{fastest.duration_seconds:.2f}s"
        )
    if slowest:
        lines.append(
            f"- Langsamste: `{slowest.model}` / `{slowest.task_id}` / "
            f"{slowest.duration_seconds:.2f}s"
        )

    if failed:
        lines.extend(["", "## Fehler"])
        for record in failed:
            lines.append(f"- `{record.model}` `{record.task_id}` run {record.run}: {record.error}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def run_benchmark(
    *,
    config: BenchmarkConfig,
    tasks: list[BenchmarkTask] | BenchmarkTaskSet,
    client: OllamaGenerateClient,
    output_dir: str | Path = Path("benchmarks") / "outputs",
    report_dir: str | Path = Path("benchmarks") / "reports",
    selected_models: Iterable[str] | None = None,
    runs_override: int | None = None,
    selected_categories: Iterable[str] | None = None,
    timestamp: str | None = None,
    run_label: str | None = None,
    run_id: str | None = None,
    resume: str | None = None,
    suite_version_override: str | None = None,
    prompt_version_override: str | None = None,
    task_version_override: str | None = None,
    archive_db: str | Path | None = DEFAULT_ARCHIVE_DB,
    no_archive: bool = False,
    health_monitor: bool = False,
    health_interval_seconds: int = 30,
    progress_mode: str = "normal",
) -> BenchmarkRunSummary:
    task_set, task_items = _task_items(
        tasks,
        prompt_version_override=prompt_version_override,
        task_version_override=task_version_override,
    )
    effective_run_id = resume or run_id or make_run_id(run_label, timestamp)
    models = filter_models(config.models, selected_models, runs_override)
    selected_tasks = filter_tasks(task_items, selected_categories)
    output_root = Path(output_dir) / effective_run_id
    progress = BenchmarkProgressTracker(
        output_dir=output_root,
        run_id=effective_run_id,
        run_label=run_label,
        total_models=len(models),
        total_tasks=len(selected_tasks),
        total_task_runs=sum(model.runs for model in models) * len(selected_tasks),
        mode=progress_mode,
    )
    progress.start_run()
    health = SystemHealthMonitor(
        output_root,
        interval_seconds=health_interval_seconds,
        enabled=health_monitor,
    )
    health_start = health.capture_snapshot("start")
    health_start_path = health.write_snapshot("system_health_start.json", health_start)
    health_samples_path = output_root / "system_health_samples.json"
    health_summary_path = output_root / "system_health_summary.json"
    system_health_metadata = {
        "start_snapshot_file": str(health_start_path),
        "end_snapshot_file": str(output_root / "system_health_end.json"),
        "samples_file": str(health_samples_path),
        "summary_file": str(health_summary_path),
        "warnings": [],
    }
    records: list[BenchmarkRecord] = []
    ollama_version = _client_ollama_version(client)
    run_metadata = _build_run_metadata(
        run_id=effective_run_id,
        run_label=run_label,
        config=config,
        task_set=task_set,
        suite_version_override=suite_version_override,
        prompt_version_override=prompt_version_override,
        task_version_override=task_version_override,
        ollama_version=ollama_version,
        system_health=system_health_metadata,
    )
    _write_run_metadata(output_root, run_metadata)
    model_metadata_by_name: dict[str, dict] = {}
    health.start_periodic()

    for model in models:
        progress.start_model(model.name)
        model_metadata = _client_model_metadata(client, model.name)
        progress.model_loaded(model.name)
        model_metadata_by_name[model.name] = model_metadata
        model_settings = {
            **config.settings.ollama_options,
            "keep_alive": model.keep_alive,
            "timeout_seconds": config.settings.timeout_seconds,
        }
        _write_model_metadata(output_root, model.name, model_metadata, model_settings)
        logger.info("Starting benchmark model group: model=%s runs=%s", model.name, model.runs)
        model_records_before = len(records)
        for run_number in range(1, model.runs + 1):
            for task_index, task in enumerate(selected_tasks, start=1):
                existing_path = (
                    output_root
                    / safe_model_name(model.name)
                    / f"{task.id}_run_{run_number}.json"
                )
                if resume and existing_path.exists():
                    record = _record_from_existing(
                        existing_path,
                        task=task,
                        model_name=model.name,
                        run_id=effective_run_id,
                        run_metadata=run_metadata,
                        model_digest=model_metadata.get("digest"),
                    )
                    records.append(record)
                    progress.finish_task(
                        model=model.name,
                        task_id=task.id,
                        run_number=run_number,
                        duration_seconds=record.duration_seconds,
                        metrics=record.metrics,
                        error=record.error,
                    )
                    logger.info("Skipping existing benchmark output: %s", existing_path)
                    continue

                logger.info(
                    "Running task: model=%s run=%s task=%s category=%s",
                    model.name,
                    run_number,
                    task.id,
                    task.category,
                )
                progress.start_task(
                    model=model.name,
                    task_id=task.id,
                    run_number=run_number,
                    task_index=task_index,
                    run_count=model.runs,
                )
                hardware_before = capture_hardware_snapshot()
                result = client.generate(
                    model=model.name,
                    prompt=task.prompt,
                    keep_alive=model.keep_alive,
                    options=config.settings.ollama_options,
                )
                hardware_after = capture_hardware_snapshot()
                metrics = build_benchmark_metrics(
                    prompt=task.prompt,
                    response=result.response,
                    raw=result.raw,
                    duration_seconds=result.duration_seconds,
                    hardware_before=hardware_before,
                    hardware_after=hardware_after,
                )
                record = BenchmarkRecord(
                    run_id=effective_run_id,
                    model=model.name,
                    model_digest=model_metadata.get("digest"),
                    task_id=task.id,
                    category=task.category,
                    run=run_number,
                    prompt=task.prompt,
                    response=result.response,
                    duration_seconds=result.duration_seconds,
                    created_at=_created_at(),
                    error=result.error,
                    task_version=task.task_version,
                    prompt_version=task.prompt_version,
                    task_hash=task.task_hash,
                    prompt_hash=task.prompt_hash,
                    config_hash=run_metadata.config_hash,
                    benchmark_suite_version=run_metadata.benchmark_suite_version,
                    careerhub_version=run_metadata.careerhub_version,
                    git_commit_hash=run_metadata.git_commit_hash,
                    git_dirty_state=run_metadata.git_dirty_state,
                    metrics=metrics,
                    metadata={
                        "title": task.title,
                        "expected_output_type": task.expected_output_type,
                        "evaluation_hints": task.evaluation_hints,
                        "options": config.settings.ollama_options,
                        "keep_alive": model.keep_alive,
                        "model_tag": model_metadata.get("tag"),
                        "model_details": model_metadata.get("details") or {},
                        "settings_hash": stable_json_hash(model_settings),
                        "ollama_raw": result.raw,
                    },
                )
                write_output_record(output_root, record)
                records.append(record)
                progress.finish_task(
                    model=model.name,
                    task_id=task.id,
                    run_number=run_number,
                    duration_seconds=result.duration_seconds,
                    metrics=metrics,
                    error=result.error,
                )
        model_records = [
            record
            for record in records[model_records_before:]
            if record.model == model.name
        ]
        write_json(
            output_root / safe_model_name(model.name) / "metrics_summary.json",
            aggregate_model_metrics(model_records),
        )
        if health_monitor:
            health.capture_sample(f"after_model:{model.name}")
        progress.finish_model(model.name)
        logger.info("Finished benchmark model group: model=%s", model.name)

    health.stop_periodic()
    health_end = health.capture_snapshot("end")
    health_end_path = health.write_snapshot("system_health_end.json", health_end)
    health_samples_path = health.write_samples()
    health_summary_path, health_summary = health.write_summary(health_start, health_end)
    system_health_metadata = {
        "start_snapshot_file": str(health_start_path),
        "end_snapshot_file": str(health_end_path),
        "samples_file": str(health_samples_path),
        "summary_file": str(health_summary_path),
        "warnings": health_summary.get("warnings", []),
        "summary": health_summary,
    }
    run_metadata = replace(run_metadata, system_health=system_health_metadata)
    _write_run_metadata(output_root, run_metadata)

    write_json(
        output_root / "run_summary.json",
        {
            "run_id": effective_run_id,
            **aggregate_run_metrics(records),
            "system_health": system_health_metadata,
        },
    )

    progress.start_report()
    progress_summary = _progress_summary(progress, records)
    report_path = generate_report(
        run_id=effective_run_id,
        run_label=run_label,
        report_dir=Path(report_dir),
        output_root=output_root,
        models=models,
        tasks=selected_tasks,
        records=records,
        run_metadata=run_metadata,
        model_metadata_by_name=model_metadata_by_name,
        progress_summary=progress_summary,
    )
    write_metrics_csv(
        Path(report_dir) / f"{effective_run_id}_metrics.csv",
        records,
    )
    progress.finish_report({"report_path": str(report_path)})
    if not no_archive and archive_db:
        progress.start_archive()
        archive = BenchmarkArchive(archive_db)
        archive_summary = archive.archive_run(output_root)
        for warning in archive_summary.warnings:
            logger.warning(warning)
        progress.finish_archive(
            {
                "archived_models": archive_summary.archived_models,
                "archived_tasks": archive_summary.archived_tasks,
                "archived_metrics": archive_summary.archived_metrics,
                "warnings": archive_summary.warnings,
            }
        )
    progress.finish_run()
    return BenchmarkRunSummary(
        run_id=effective_run_id,
        output_root=output_root,
        report_path=report_path,
        run_metadata=run_metadata,
        records=records,
        model_order=[model.name for model in models],
        progress_summary=progress_summary,
    )


def _progress_summary(progress: BenchmarkProgressTracker, records: list[BenchmarkRecord]) -> dict:
    durations = [record.duration_seconds for record in records]
    sorted_records = sorted(records, key=lambda record: record.duration_seconds)
    return {
        "started_at": progress.state.started_at,
        "finished_at": progress.state.updated_at,
        "total_duration_seconds": progress.state.elapsed_seconds,
        "completed_task_runs": progress.state.completed_task_runs,
        "failed_task_runs": progress.state.failed_task_runs,
        "average_task_duration_seconds": round(sum(durations) / len(durations), 3) if durations else None,
        "slowest_task": _progress_task_ref(sorted_records[-1]) if sorted_records else None,
        "fastest_task": _progress_task_ref(sorted_records[0]) if sorted_records else None,
    }


def _progress_task_ref(record: BenchmarkRecord) -> dict:
    return {
        "model": record.model,
        "task_id": record.task_id,
        "run": record.run,
        "duration_seconds": record.duration_seconds,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local CareerHub Ollama benchmarks.")
    parser.add_argument("--config", default="config/benchmark_models.yaml")
    parser.add_argument("--models", nargs="*")
    parser.add_argument("--runs", type=int)
    parser.add_argument("--tasks", help="Comma separated categories, e.g. careerhub,coding")
    parser.add_argument("--output-dir", default=str(Path("benchmarks") / "outputs"))
    parser.add_argument("--report-dir", default=str(Path("benchmarks") / "reports"))
    parser.add_argument("--run-label")
    parser.add_argument("--suite-version")
    parser.add_argument("--prompt-version")
    parser.add_argument("--task-version")
    parser.add_argument("--resume")
    parser.add_argument("--archive-db", default=str(DEFAULT_ARCHIVE_DB))
    parser.add_argument("--no-archive", action="store_true")
    parser.add_argument("--health-monitor", action="store_true")
    parser.add_argument("--health-interval-seconds", type=int, default=30)
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--progress-json-only", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def _progress_mode(args: argparse.Namespace) -> str:
    if args.progress_json_only:
        return "json_only"
    if args.quiet:
        return "quiet"
    return "normal"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _parse_args()
    config = load_benchmark_config(args.config)
    task_set = load_benchmark_task_set(config.settings.tasks_path)
    selected_categories = args.tasks.split(",") if args.tasks else None
    client = OllamaGenerateClient(timeout_seconds=config.settings.timeout_seconds)
    summary = run_benchmark(
        config=config,
        tasks=task_set,
        client=client,
        output_dir=args.output_dir,
        report_dir=args.report_dir,
        selected_models=args.models,
        runs_override=args.runs,
        selected_categories=selected_categories,
        run_label=args.run_label,
        resume=args.resume,
        suite_version_override=args.suite_version,
        prompt_version_override=args.prompt_version,
        task_version_override=args.task_version,
        archive_db=args.archive_db,
        no_archive=args.no_archive,
        health_monitor=args.health_monitor,
        health_interval_seconds=args.health_interval_seconds,
        progress_mode=_progress_mode(args),
    )
    print(f"Benchmark abgeschlossen: {summary.report_path}")


if __name__ == "__main__":
    main()
