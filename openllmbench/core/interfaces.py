from __future__ import annotations

from pathlib import Path
from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from openllmbench.core.models import (
    BenchmarkRunContext,
    BenchmarkTask,
    Capability,
    EvaluationResult,
    GenerateRequest,
    GenerateResult,
    ModelInfo,
    Prompt,
    PromptTemplate,
)
from openllmbench.judges.models import JudgeConsensus, JudgePipeline, JudgeProfile, JudgeResult, JudgeRubric
from openllmbench.providers.models import (
    ProviderHealth,
    ProviderKeepAliveResult,
    ProviderMetadata,
    ProviderModelInfo,
    ProviderShutdownResult,
    ProviderStreamEvent,
)


@runtime_checkable
class BenchmarkSuite(Protocol):
    id: str
    version: str

    def load_tasks(self) -> list[BenchmarkTask]:
        ...


@runtime_checkable
class PromptBuilder(Protocol):
    id: str
    version: str

    def build_prompt(self, task: BenchmarkTask, template: PromptTemplate) -> Prompt:
        ...


@runtime_checkable
class ModelProvider(Protocol):
    id: str
    version: str

    def list_models(self) -> list[ModelInfo]:
        ...

    def models(self) -> list[ProviderModelInfo]:
        ...

    def generate(self, request: GenerateRequest) -> GenerateResult:
        ...

    def stream(self, request: GenerateRequest) -> Iterable[ProviderStreamEvent]:
        ...

    def health(self) -> ProviderHealth:
        ...

    def metadata(self) -> ProviderMetadata:
        ...

    def keep_alive(self, model_name: str) -> ProviderKeepAliveResult:
        ...

    def shutdown(self) -> ProviderShutdownResult:
        ...


@runtime_checkable
class TelemetryProvider(Protocol):
    id: str
    version: str

    def on_run_start(self, context: BenchmarkRunContext) -> None:
        ...

    def on_run_end(self, context: BenchmarkRunContext) -> None:
        ...


@runtime_checkable
class ArchiveBackend(Protocol):
    id: str
    version: str

    def archive_run(self, run_dir: Path) -> object:
        ...


@runtime_checkable
class Reporter(Protocol):
    id: str
    version: str

    def write_report(self, context: BenchmarkRunContext) -> Path:
        ...


@runtime_checkable
class Evaluator(Protocol):
    id: str
    version: str

    def evaluate(self, task: BenchmarkTask, result: GenerateResult) -> EvaluationResult:
        ...


@runtime_checkable
class Judge(Protocol):
    id: str
    version: str

    def judge(self, task: BenchmarkTask, result: GenerateResult) -> JudgeResult:
        ...


@runtime_checkable
class JudgeConsensusProvider(Protocol):
    id: str
    version: str

    def build_consensus(self, results: list[JudgeResult], profile: JudgeProfile) -> JudgeConsensus:
        ...


@runtime_checkable
class JudgePipelineProvider(Protocol):
    id: str
    version: str

    def load_pipeline(self, pipeline_id: str) -> JudgePipeline:
        ...

    def load_rubric(self, rubric_id: str) -> JudgeRubric:
        ...


@runtime_checkable
class CapabilityProvider(Protocol):
    id: str
    version: str

    def list_capabilities(self) -> list[Capability]:
        ...
