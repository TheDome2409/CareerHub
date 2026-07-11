from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from openllmbench.core.models import VersionedModel


@dataclass(frozen=True)
class RunMetadata(VersionedModel):
    run_label: str | None = None
    suite_id: str = ""
    provider_id: str = ""
    git_commit_hash: str | None = None
    git_dirty_state: str | None = None
    environment: dict[str, Any] = field(default_factory=dict)

