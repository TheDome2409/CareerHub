from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class VersionedModel:
    id: str
    version: str
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    description: str | None = None


class CapabilityId(str, Enum):
    CODING = "coding"
    ANALYSIS = "analysis"
    DOCUMENTATION = "documentation"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    REASONING = "reasoning"
    CAREER_MATCHING = "career_matching"
    PROJECT_MANAGEMENT = "project_management"
    NATURAL_LANGUAGE = "natural_language"
    LONG_CONTEXT = "long_context"
    TRANSLATION = "translation"


@dataclass(frozen=True)
class Capability(VersionedModel):
    label: str = ""


DEFAULT_CAPABILITIES: tuple[Capability, ...] = (
    Capability(id=CapabilityId.CODING.value, version="1.0", label="Coding"),
    Capability(id=CapabilityId.ANALYSIS.value, version="1.0", label="Analysis"),
    Capability(id=CapabilityId.DOCUMENTATION.value, version="1.0", label="Documentation"),
    Capability(id=CapabilityId.ARCHITECTURE.value, version="1.0", label="Architecture"),
    Capability(id=CapabilityId.SECURITY.value, version="1.0", label="Security"),
    Capability(id=CapabilityId.REASONING.value, version="1.0", label="Reasoning"),
    Capability(id=CapabilityId.CAREER_MATCHING.value, version="1.0", label="Career Matching"),
    Capability(id=CapabilityId.PROJECT_MANAGEMENT.value, version="1.0", label="Project Management"),
    Capability(id=CapabilityId.NATURAL_LANGUAGE.value, version="1.0", label="Natural Language"),
    Capability(id=CapabilityId.LONG_CONTEXT.value, version="1.0", label="Long Context"),
    Capability(id=CapabilityId.TRANSLATION.value, version="1.0", label="Translation"),
)


@dataclass(frozen=True)
class PromptTemplate(VersionedModel):
    name: str = ""
    template: str = ""
    capability_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PromptVersion(VersionedModel):
    prompt_template_id: str = ""
    changelog: str | None = None


@dataclass(frozen=True)
class BenchmarkTask(VersionedModel):
    category: str = ""
    title: str = ""
    prompt_template_id: str = ""
    expected_output_type: str = ""
    evaluation_hints: list[str] = field(default_factory=list)
    capability_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Prompt:
    task_id: str
    prompt_template_id: str
    prompt_version_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelInfo(VersionedModel):
    provider_id: str = ""
    name: str = ""
    digest: str | None = None
    capability_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GenerateRequest:
    model_name: str
    prompt: Prompt
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerateResult:
    request: GenerateRequest
    response_text: str
    created_at: str = field(default_factory=utc_now_iso)
    raw: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class EvaluationResult(VersionedModel):
    task_id: str = ""
    model_name: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class JudgeResult(VersionedModel):
    task_id: str = ""
    model_name: str = ""
    score: float | None = None
    rationale: str | None = None


@dataclass(frozen=True)
class BenchmarkRunContext:
    run_id: str
    suite_id: str
    provider_id: str
    output_dir: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BenchmarkPipeline:
    id: str = "default_benchmark_pipeline"
    version: str = "1.0"
    steps: tuple[str, ...] = (
        "Task",
        "PromptBuilder",
        "Prompt",
        "Provider",
        "Model",
        "Telemetry",
        "Archive",
        "Evaluation",
        "Judge",
        "Reporter",
        "Output",
    )
    description: str = (
        "Task -> PromptBuilder -> Prompt -> Provider -> Model -> Telemetry "
        "-> Archive -> Evaluation -> Judge -> Reporter -> Output"
    )

