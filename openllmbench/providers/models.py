from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProviderModelInfo:
    provider_id: str
    name: str
    tag: str | None = None
    digest: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    capability_ids: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderHealth:
    provider_id: str
    available: bool
    status: str
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderMetadata:
    provider_id: str
    name: str
    version: str | None = None
    base_url: str | None = None
    capabilities: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderStreamEvent:
    text: str = ""
    done: bool = False
    raw: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class ProviderKeepAliveResult:
    provider_id: str
    model_name: str
    success: bool
    message: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderShutdownResult:
    provider_id: str
    success: bool
    message: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
