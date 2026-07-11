from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from openllmbench.core.models import VersionedModel


@dataclass(frozen=True)
class BenchmarkConfig(VersionedModel):
    suite_id: str = ""
    provider_id: str = ""
    model_names: list[str] = field(default_factory=list)
    runs: int = 1
    settings: dict[str, Any] = field(default_factory=dict)

