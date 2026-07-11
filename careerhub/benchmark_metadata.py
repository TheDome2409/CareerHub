from __future__ import annotations

import hashlib
import json
import os
import platform as platform_module
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GitMetadata:
    commit_hash: str | None
    branch: str | None
    dirty_state: str


@dataclass(frozen=True)
class BenchmarkRunMetadata:
    run_id: str
    run_label: str | None
    created_at: str
    careerhub_version: str
    git_commit_hash: str | None
    git_branch: str | None
    git_dirty_state: str
    benchmark_suite_version: str
    task_set_version: str
    prompt_set_version: str
    config_hash: str
    task_file_hash: str | None
    ollama_version: str | None
    python_version: str
    platform: str
    hardware_summary: dict[str, Any]
    settings: dict[str, Any]
    system_health: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_json_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def stable_text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def stable_file_hash(path: str | Path) -> str | None:
    file_path = Path(path)
    if not file_path.exists():
        return None
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def git_metadata(cwd: str | Path | None = None) -> GitMetadata:
    repo = Path(cwd or ".")

    def _git(args: list[str]) -> str | None:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=repo,
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
            return result.stdout.strip()
        except Exception:
            return None

    commit = _git(["rev-parse", "HEAD"])
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    status = _git(["status", "--porcelain"])
    if commit is None:
        dirty = "unknown"
    elif status:
        dirty = "dirty"
    else:
        dirty = "clean"
    return GitMetadata(commit_hash=commit, branch=branch, dirty_state=dirty)


def hardware_summary() -> dict[str, Any]:
    return {
        "machine": platform_module.machine(),
        "processor": platform_module.processor(),
        "cpu_count": os.cpu_count(),
    }


def careerhub_version() -> str:
    try:
        import jobagent  # type: ignore

        version = getattr(jobagent, "__version__", None)
        if version:
            return str(version)
    except Exception:
        pass
    return "local"


def make_run_id(label: str | None = None, timestamp: str | None = None) -> str:
    stamp = timestamp or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if not label:
        return stamp
    safe_label = []
    for char in label.lower().strip():
        if char.isalnum():
            safe_label.append(char)
        elif char in {"-", "_", " ", ".", ":"}:
            safe_label.append("_")
    safe = "".join(safe_label).strip("_") or "run"
    while "__" in safe:
        safe = safe.replace("__", "_")
    return f"{stamp}_{safe}"
