from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


PLUGIN_TYPES = {
    "providers",
    "suites",
    "telemetry",
    "archive",
    "reporters",
    "evaluators",
    "judges",
    "capabilities",
}


@dataclass
class PluginRegistry:
    providers: dict[str, Any] = field(default_factory=dict)
    suites: dict[str, Any] = field(default_factory=dict)
    telemetry: dict[str, Any] = field(default_factory=dict)
    archive: dict[str, Any] = field(default_factory=dict)
    reporters: dict[str, Any] = field(default_factory=dict)
    evaluators: dict[str, Any] = field(default_factory=dict)
    judges: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)

    def register(self, plugin_type: str, plugin_id: str, plugin: Any) -> None:
        self._bucket(plugin_type)[plugin_id] = plugin

    def get(self, plugin_type: str, plugin_id: str) -> Any:
        return self._bucket(plugin_type)[plugin_id]

    def list(self, plugin_type: str) -> list[str]:
        return sorted(self._bucket(plugin_type).keys())

    def register_provider(self, plugin_id: str, plugin: Any) -> None:
        self.register("providers", plugin_id, plugin)

    def register_suite(self, plugin_id: str, plugin: Any) -> None:
        self.register("suites", plugin_id, plugin)

    def register_telemetry(self, plugin_id: str, plugin: Any) -> None:
        self.register("telemetry", plugin_id, plugin)

    def register_archive(self, plugin_id: str, plugin: Any) -> None:
        self.register("archive", plugin_id, plugin)

    def register_reporter(self, plugin_id: str, plugin: Any) -> None:
        self.register("reporters", plugin_id, plugin)

    def register_evaluator(self, plugin_id: str, plugin: Any) -> None:
        self.register("evaluators", plugin_id, plugin)

    def register_judge(self, plugin_id: str, plugin: Any) -> None:
        self.register("judges", plugin_id, plugin)

    def register_capability(self, plugin_id: str, plugin: Any) -> None:
        self.register("capabilities", plugin_id, plugin)

    def _bucket(self, plugin_type: str) -> dict[str, Any]:
        if plugin_type not in PLUGIN_TYPES:
            raise KeyError(f"Unknown plugin type: {plugin_type}")
        return getattr(self, plugin_type)


default_registry = PluginRegistry()

