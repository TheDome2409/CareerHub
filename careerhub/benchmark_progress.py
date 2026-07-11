from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PHASES = {
    "initializing",
    "loading_model",
    "running_task",
    "saving_output",
    "archiving",
    "reporting",
    "finished",
    "failed",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _format_seconds(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


@dataclass
class BenchmarkProgressState:
    run_id: str
    run_label: str | None
    started_at: str
    updated_at: str
    current_model: str | None = None
    current_task: str | None = None
    current_run: int | None = None
    total_models: int = 0
    completed_models: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    total_task_runs: int = 0
    completed_task_runs: int = 0
    failed_task_runs: int = 0
    percent_complete: float = 0.0
    elapsed_seconds: float = 0.0
    estimated_total_seconds: float | None = None
    eta_seconds: float | None = None
    eta_human: str | None = None
    current_phase: str = "initializing"

    def update_timing(self) -> None:
        now = datetime.now(timezone.utc)
        started = _parse_iso(self.started_at)
        self.updated_at = utc_now_iso()
        self.elapsed_seconds = round((now - started).total_seconds(), 3)
        if self.total_task_runs > 0:
            self.percent_complete = round(
                min(100.0, (self.completed_task_runs / self.total_task_runs) * 100),
                2,
            )
        if self.completed_task_runs > 0 and self.total_task_runs > 0:
            avg = self.elapsed_seconds / self.completed_task_runs
            self.estimated_total_seconds = round(avg * self.total_task_runs, 3)
            self.eta_seconds = round(max(0.0, self.estimated_total_seconds - self.elapsed_seconds), 3)
            self.eta_human = _format_seconds(self.eta_seconds)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkProgressEvent:
    created_at: str
    event_type: str
    run_id: str
    model: str | None = None
    task_id: str | None = None
    run_number: int | None = None
    message: str = ""
    progress_percent: float = 0.0
    duration_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BenchmarkProgressTracker:
    def __init__(
        self,
        *,
        output_dir: str | Path,
        run_id: str,
        run_label: str | None,
        total_models: int,
        total_tasks: int,
        total_task_runs: int,
        mode: str = "normal",
        stream=None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.state_path = self.output_dir / "progress_state.json"
        self.events_path = self.output_dir / "progress_events.jsonl"
        self.mode = mode
        self.stream = stream or sys.stdout
        now = utc_now_iso()
        self.state = BenchmarkProgressState(
            run_id=run_id,
            run_label=run_label,
            started_at=now,
            updated_at=now,
            total_models=total_models,
            total_tasks=total_tasks,
            total_task_runs=total_task_runs,
        )

    @property
    def quiet(self) -> bool:
        return self.mode in {"quiet", "json_only"}

    def start_run(self) -> None:
        self.state.current_phase = "initializing"
        self._emit("run_started", f"[OpenLLMBench] Run {self.state.run_id}")

    def start_model(self, model: str) -> None:
        self.state.current_model = model
        self.state.current_phase = "loading_model"
        self._emit("model_started", f"Model {self.state.completed_models + 1}/{self.state.total_models}: {model}", model=model)

    def model_loaded(self, model: str) -> None:
        self._emit("model_loaded", f"Model loaded: {model}", model=model)

    def finish_model(self, model: str) -> None:
        self.state.completed_models += 1
        self._emit("model_finished", f"Model finished: {model}", model=model)

    def start_task(self, *, model: str, task_id: str, run_number: int, task_index: int, run_count: int) -> None:
        self.state.current_model = model
        self.state.current_task = task_id
        self.state.current_run = run_number
        self.state.current_phase = "running_task"
        message = (
            f"Task {task_index}/{self.state.total_tasks}: {task_id} | "
            f"Run {run_number}/{run_count}"
        )
        self._emit("task_started", message, model=model, task_id=task_id, run_number=run_number)

    def finish_task(
        self,
        *,
        model: str,
        task_id: str,
        run_number: int,
        duration_seconds: float,
        metrics: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        self.state.current_phase = "saving_output"
        self.state.completed_task_runs += 1
        if error:
            self.state.failed_task_runs += 1
        self.state.completed_tasks = min(self.state.total_tasks, self.state.completed_task_runs)
        metrics = metrics or {}
        token_metrics = metrics.get("token_metrics") or {}
        perf = metrics.get("performance_metrics") or {}
        total_tokens = token_metrics.get("total_tokens")
        total_tps = perf.get("total_tokens_per_second")
        if error:
            message = f"✗ {task_id} run {run_number} failed in {duration_seconds:.1f}s | {error}"
            event_type = "task_failed"
        else:
            token_text = f" | {total_tps:.1f} tok/s | {total_tokens:,} tokens" if total_tps and total_tokens else ""
            message = f"✓ {task_id} run {run_number} finished in {duration_seconds:.1f}s{token_text}"
            event_type = "task_finished"
        self._emit(
            event_type,
            message,
            model=model,
            task_id=task_id,
            run_number=run_number,
            duration_seconds=duration_seconds,
            metadata={"metrics": metrics, "error": error},
            force_terminal=bool(error),
        )

    def start_archive(self) -> None:
        self.state.current_phase = "archiving"
        self._emit("archive_started", "Archiving benchmark run")

    def finish_archive(self, metadata: dict[str, Any] | None = None) -> None:
        self._emit("archive_finished", "Archive finished", metadata=metadata or {})

    def start_report(self) -> None:
        self.state.current_phase = "reporting"
        self._emit("report_started", "Writing benchmark reports")

    def finish_report(self, metadata: dict[str, Any] | None = None) -> None:
        self._emit("report_finished", "Reports written", metadata=metadata or {})

    def finish_run(self) -> None:
        self.state.current_phase = "finished"
        self._emit("run_finished", f"Run finished: {self.state.run_id}")

    def fail_run(self, error: str) -> None:
        self.state.current_phase = "failed"
        self._emit("run_failed", f"Run failed: {error}", metadata={"error": error}, force_terminal=True)

    def _emit(
        self,
        event_type: str,
        message: str,
        *,
        model: str | None = None,
        task_id: str | None = None,
        run_number: int | None = None,
        duration_seconds: float | None = None,
        metadata: dict[str, Any] | None = None,
        force_terminal: bool = False,
    ) -> None:
        self.state.update_timing()
        event = BenchmarkProgressEvent(
            created_at=utc_now_iso(),
            event_type=event_type,
            run_id=self.state.run_id,
            model=model,
            task_id=task_id,
            run_number=run_number,
            message=message,
            progress_percent=self.state.percent_complete,
            duration_seconds=duration_seconds,
            metadata=metadata or {},
        )
        self._write_state()
        self._append_event(event)
        self._print(message, force=force_terminal)

    def _write_state(self) -> None:
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(
                json.dumps(self.state.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _append_event(self, event: BenchmarkProgressEvent) -> None:
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            with self.events_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _print(self, message: str, *, force: bool = False) -> None:
        if self.mode == "json_only":
            return
        if self.mode == "quiet" and not force and self.state.current_phase not in {"finished", "failed"}:
            return
        eta = f" | ETA {self.state.eta_human}" if self.state.eta_human else ""
        progress = f" | Progress {self.state.percent_complete:.1f}% | elapsed {_format_seconds(self.state.elapsed_seconds)}"
        try:
            print(f"{message}{progress}{eta}", file=self.stream)
        except Exception:
            pass
