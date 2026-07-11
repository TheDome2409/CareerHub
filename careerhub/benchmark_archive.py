from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from careerhub.benchmark_models import safe_model_name

try:
    import duckdb  # type: ignore
except Exception:  # pragma: no cover - depends on local optional dependency.
    duckdb = None


DEFAULT_ARCHIVE_DB = Path("benchmarks") / "archive" / "careerhub_benchmarks.duckdb"


@dataclass
class ArchiveSummary:
    run_id: str | None
    db_path: Path
    archived_models: int = 0
    archived_tasks: int = 0
    archived_metrics: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def archived(self) -> bool:
        return not self.warnings or any("DuckDB nicht installiert" not in item for item in self.warnings)


class BenchmarkArchive:
    def __init__(self, db_path: str | Path = DEFAULT_ARCHIVE_DB) -> None:
        self.db_path = Path(db_path)

    @property
    def available(self) -> bool:
        return duckdb is not None

    def _connect(self):
        if duckdb is None:
            raise RuntimeError("DuckDB nicht installiert, Archivierung übersprungen.")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return duckdb.connect(str(self.db_path))

    def init_schema(self) -> None:
        if not self.available:
            return
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    run_label TEXT,
                    created_at TEXT,
                    careerhub_version TEXT,
                    git_commit_hash TEXT,
                    git_branch TEXT,
                    git_dirty_state TEXT,
                    benchmark_suite_version TEXT,
                    task_set_version TEXT,
                    prompt_set_version TEXT,
                    config_hash TEXT,
                    task_file_hash TEXT,
                    ollama_version TEXT,
                    python_version TEXT,
                    platform TEXT,
                    hardware_summary_json TEXT,
                    settings_json TEXT,
                    system_health_summary_json TEXT,
                    output_dir TEXT
                )
                """
            )
            self._ensure_column(con, "runs", "system_health_summary_json", "TEXT")
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS models (
                    run_id TEXT,
                    model_name TEXT,
                    model_tag TEXT,
                    model_digest TEXT,
                    parameter_size TEXT,
                    quantization_level TEXT,
                    context_length BIGINT,
                    embedding_length BIGINT,
                    capabilities_json TEXT,
                    settings_hash TEXT,
                    raw_json TEXT,
                    PRIMARY KEY (run_id, model_name)
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    run_id TEXT,
                    model_name TEXT,
                    task_id TEXT,
                    category TEXT,
                    run_number INTEGER,
                    task_version TEXT,
                    prompt_version TEXT,
                    task_hash TEXT,
                    prompt_hash TEXT,
                    prompt_text TEXT,
                    response_text TEXT,
                    duration_seconds DOUBLE,
                    created_at TEXT,
                    error TEXT,
                    output_file TEXT,
                    PRIMARY KEY (run_id, model_name, task_id, run_number)
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    run_id TEXT,
                    model_name TEXT,
                    task_id TEXT,
                    run_number INTEGER,
                    prompt_tokens BIGINT,
                    completion_tokens BIGINT,
                    total_tokens BIGINT,
                    prompt_tps DOUBLE,
                    completion_tps DOUBLE,
                    total_tps DOUBLE,
                    load_time_ms DOUBLE,
                    generation_time_ms DOUBLE,
                    total_time_ms DOUBLE,
                    prompt_characters BIGINT,
                    completion_characters BIGINT,
                    prompt_words BIGINT,
                    completion_words BIGINT,
                    prompt_lines BIGINT,
                    completion_lines BIGINT,
                    response_size_bytes BIGINT,
                    generation_ratio DOUBLE,
                    prompt_completion_ratio DOUBLE,
                    characters_per_token_prompt DOUBLE,
                    characters_per_token_completion DOUBLE,
                    PRIMARY KEY (run_id, model_name, task_id, run_number)
                )
                """
            )

    def archive_run(self, run_dir: str | Path) -> ArchiveSummary:
        run_path = Path(run_dir)
        metadata_path = run_path / "run_metadata.json"
        summary = ArchiveSummary(run_id=run_path.name, db_path=self.db_path)
        if not self.available:
            summary.warnings.append("DuckDB nicht installiert, Archivierung übersprungen.")
            self._write_archive_summary(run_path, summary)
            return summary
        if not metadata_path.exists():
            summary.warnings.append(f"run_metadata.json nicht gefunden: {metadata_path}")
            self._write_archive_summary(run_path, summary)
            return summary

        self.init_schema()
        run_metadata = _read_json(metadata_path)
        run_id = str(run_metadata.get("run_id") or run_path.name)
        summary.run_id = run_id
        with self._connect() as con:
            self._delete_run(con, run_id)
            self.archive_run_metadata(con, run_metadata, run_path)
            for model_dir in _model_dirs(run_path):
                model_metadata_path = model_dir / "model_metadata.json"
                if model_metadata_path.exists():
                    self.archive_model_metadata(con, run_id, _read_json(model_metadata_path))
                    summary.archived_models += 1
                for task_file in sorted(model_dir.glob("*_run_*.json")):
                    task_payload = _read_json(task_file)
                    self.archive_task_result(con, task_payload, task_file)
                    self.archive_metrics(con, task_payload)
                    summary.archived_tasks += 1
                    summary.archived_metrics += 1
        self._write_archive_summary(run_path, summary)
        return summary

    def archive_run_metadata(self, con, metadata: dict[str, Any], run_path: Path) -> None:
        con.execute(
            """
            INSERT INTO runs (
                run_id,
                run_label,
                created_at,
                careerhub_version,
                git_commit_hash,
                git_branch,
                git_dirty_state,
                benchmark_suite_version,
                task_set_version,
                prompt_set_version,
                config_hash,
                task_file_hash,
                ollama_version,
                python_version,
                platform,
                hardware_summary_json,
                settings_json,
                system_health_summary_json,
                output_dir
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                metadata.get("run_id"),
                metadata.get("run_label"),
                metadata.get("created_at"),
                metadata.get("careerhub_version"),
                metadata.get("git_commit_hash"),
                metadata.get("git_branch"),
                metadata.get("git_dirty_state"),
                metadata.get("benchmark_suite_version"),
                metadata.get("task_set_version"),
                metadata.get("prompt_set_version"),
                metadata.get("config_hash"),
                metadata.get("task_file_hash"),
                metadata.get("ollama_version"),
                metadata.get("python_version"),
                metadata.get("platform"),
                _json(metadata.get("hardware_summary")),
                _json(metadata.get("settings")),
                _json((metadata.get("system_health") or {}).get("summary")),
                str(run_path),
            ],
        )

    def archive_model_metadata(self, con, run_id: str, metadata: dict[str, Any]) -> None:
        capability = metadata.get("capability_metadata") or {}
        con.execute(
            """
            INSERT INTO models VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                metadata.get("model_name"),
                metadata.get("model_tag"),
                metadata.get("model_digest"),
                _string_or_none(capability.get("parameter_size")),
                _string_or_none(capability.get("quantization") or capability.get("quantization_level")),
                _int_or_none(capability.get("context_length")),
                _int_or_none(capability.get("embedding_length")),
                _json(capability.get("capabilities")),
                metadata.get("settings_hash"),
                _json(metadata.get("raw")),
            ],
        )

    def archive_task_result(self, con, payload: dict[str, Any], output_file: Path) -> None:
        con.execute(
            """
            INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                payload.get("run_id"),
                payload.get("model"),
                payload.get("task_id"),
                payload.get("category"),
                payload.get("run"),
                payload.get("task_version"),
                payload.get("prompt_version"),
                payload.get("task_hash"),
                payload.get("prompt_hash"),
                payload.get("prompt"),
                payload.get("response"),
                payload.get("duration_seconds"),
                payload.get("created_at"),
                payload.get("error"),
                str(output_file),
            ],
        )

    def archive_metrics(self, con, payload: dict[str, Any]) -> None:
        metrics = payload.get("metrics") or {}
        token = metrics.get("token_metrics") or {}
        timing = metrics.get("timing_metrics") or {}
        perf = metrics.get("performance_metrics") or {}
        con.execute(
            """
            INSERT INTO metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                payload.get("run_id"),
                payload.get("model"),
                payload.get("task_id"),
                payload.get("run"),
                token.get("prompt_tokens"),
                token.get("completion_tokens"),
                token.get("total_tokens"),
                perf.get("prompt_tokens_per_second"),
                perf.get("completion_tokens_per_second"),
                perf.get("total_tokens_per_second"),
                timing.get("load_time_ms"),
                timing.get("generation_time_ms"),
                timing.get("total_time_ms"),
                perf.get("prompt_characters"),
                perf.get("completion_characters"),
                perf.get("prompt_words"),
                perf.get("completion_words"),
                perf.get("prompt_lines"),
                perf.get("completion_lines"),
                perf.get("response_size_bytes"),
                timing.get("generation_ratio"),
                token.get("prompt_completion_ratio"),
                perf.get("characters_per_token_prompt"),
                perf.get("characters_per_token_completion"),
            ],
        )

    def list_runs(self) -> list[dict[str, Any]]:
        if not self.available:
            return []
        self.init_schema()
        with self._connect() as con:
            return _rows(
                con,
                """
                SELECT run_id, run_label, created_at, git_commit_hash, git_dirty_state, output_dir
                FROM runs
                ORDER BY created_at DESC
                """,
            )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        if not self.available:
            return None
        self.init_schema()
        with self._connect() as con:
            rows = _rows(con, "SELECT * FROM runs WHERE run_id = ?", [run_id])
            return rows[0] if rows else None

    def compare_models(self, run_id: str) -> list[dict[str, Any]]:
        if not self.available:
            return []
        self.init_schema()
        with self._connect() as con:
            return _rows(
                con,
                """
                SELECT
                    model_name,
                    COUNT(*) AS task_runs,
                    SUM(total_tokens) AS total_tokens,
                    AVG(total_tps) AS avg_total_tps,
                    AVG(total_time_ms) AS avg_total_time_ms,
                    AVG(completion_characters) AS avg_response_chars
                FROM metrics
                WHERE run_id = ?
                GROUP BY model_name
                ORDER BY model_name
                """,
                [run_id],
            )

    def compare_runs(self, run_ids: list[str]) -> list[dict[str, Any]]:
        if not self.available or not run_ids:
            return []
        self.init_schema()
        placeholders = ", ".join(["?"] * len(run_ids))
        with self._connect() as con:
            return _rows(
                con,
                f"""
                SELECT
                    run_id,
                    COUNT(*) AS task_runs,
                    SUM(total_tokens) AS total_tokens,
                    AVG(total_tps) AS avg_total_tps,
                    AVG(total_time_ms) AS avg_total_time_ms
                FROM metrics
                WHERE run_id IN ({placeholders})
                GROUP BY run_id
                ORDER BY run_id
                """,
                run_ids,
            )

    def _delete_run(self, con, run_id: str) -> None:
        for table in ["metrics", "tasks", "models", "runs"]:
            con.execute(f"DELETE FROM {table} WHERE run_id = ?", [run_id])

    def _ensure_column(self, con, table: str, column: str, column_type: str) -> None:
        try:
            columns = con.execute(f"PRAGMA table_info('{table}')").fetchall()
            existing = {row[1] for row in columns}
            if column not in existing:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
        except Exception:
            pass

    def _write_archive_summary(self, run_path: Path, summary: ArchiveSummary) -> Path:
        reports_dir = run_path.parent.parent / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        run_id = summary.run_id or run_path.name
        path = reports_dir / f"{run_id}_archive_summary.md"
        lines = [
            "# CareerHub Benchmark Archive Summary",
            "",
            f"Run ID: `{run_id}`",
            f"DB: `{summary.db_path}`",
            f"Archivierte Modelle: {summary.archived_models}",
            f"Archivierte Tasks: {summary.archived_tasks}",
            f"Archivierte Metrics-Zeilen: {summary.archived_metrics}",
            "",
            "## Beispielabfrage",
            "",
            "```powershell",
            f"python -m careerhub.benchmark_archive --db {summary.db_path} --compare-models {run_id}",
            "```",
        ]
        if summary.warnings:
            lines.extend(["", "## Warnungen"])
            lines.extend(f"- {warning}" for warning in summary.warnings)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _rows(con, query: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
    result = con.execute(query, params or [])
    columns = [item[0] for item in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def _model_dirs(run_path: Path) -> list[Path]:
    return [
        path
        for path in sorted(run_path.iterdir())
        if path.is_dir() and (path / "model_metadata.json").exists()
    ]


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _print_table(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print("Keine Daten gefunden.")
        return
    columns = list(rows[0].keys())
    print("| " + " | ".join(columns) + " |")
    print("| " + " | ".join("---" for _ in columns) + " |")
    for row in rows:
        print("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CareerHub Benchmark DuckDB archive.")
    parser.add_argument("--db", default=str(DEFAULT_ARCHIVE_DB))
    parser.add_argument("--archive-run")
    parser.add_argument("--list-runs", action="store_true")
    parser.add_argument("--compare-models")
    parser.add_argument("--compare-runs", nargs="*")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    archive = BenchmarkArchive(args.db)
    if not archive.available:
        print("DuckDB nicht installiert, Archivierung übersprungen.")
        return
    if args.archive_run:
        summary = archive.archive_run(args.archive_run)
        print(
            f"Archiviert: models={summary.archived_models}, "
            f"tasks={summary.archived_tasks}, metrics={summary.archived_metrics}"
        )
        return
    if args.list_runs:
        _print_table(archive.list_runs())
        return
    if args.compare_models:
        _print_table(archive.compare_models(args.compare_models))
        return
    if args.compare_runs:
        _print_table(archive.compare_runs(args.compare_runs))
        return
    print("Keine Aktion angegeben. Nutze --list-runs, --compare-models, --compare-runs oder --archive-run.")


if __name__ == "__main__":
    main()
