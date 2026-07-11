import subprocess
import sys

from openllmbench.core.interfaces import BenchmarkSuite, ModelProvider
from openllmbench.core.models import (
    BenchmarkPipeline,
    BenchmarkTask,
    CapabilityId,
    DEFAULT_CAPABILITIES,
    GenerateRequest,
    GenerateResult,
    ModelInfo,
    Prompt,
    PromptTemplate,
    PromptVersion,
)
from openllmbench.core.registry import PluginRegistry
from openllmbench.providers.models import (
    ProviderHealth,
    ProviderKeepAliveResult,
    ProviderMetadata,
    ProviderShutdownResult,
)


class DummySuite:
    id = "dummy_suite"
    version = "1.0"

    def load_tasks(self):
        return []


class DummyProvider:
    id = "dummy_provider"
    version = "1.0"

    def list_models(self):
        return []

    def models(self):
        return []

    def generate(self, request):
        return GenerateResult(request=request, response_text="ok")

    def stream(self, request):
        return iter(())

    def health(self):
        return ProviderHealth(provider_id=self.id, available=True, status="available")

    def metadata(self):
        return ProviderMetadata(provider_id=self.id, name="Dummy")

    def keep_alive(self, model_name):
        return ProviderKeepAliveResult(provider_id=self.id, model_name=model_name, success=True)

    def shutdown(self):
        return ProviderShutdownResult(provider_id=self.id, success=True)


def test_openllmbench_imports():
    import openllmbench
    import openllmbench.archive.base
    import openllmbench.evaluators.base
    import openllmbench.judges.base
    import openllmbench.providers.base
    import openllmbench.reports.base
    import openllmbench.suites.base
    import openllmbench.telemetry.base

    assert openllmbench.__version__


def test_capabilities_have_expected_ids():
    capability_ids = {capability.id for capability in DEFAULT_CAPABILITIES}

    assert CapabilityId.CODING.value in capability_ids
    assert CapabilityId.ANALYSIS.value in capability_ids
    assert CapabilityId.CAREER_MATCHING.value in capability_ids
    assert CapabilityId.LONG_CONTEXT.value in capability_ids
    assert len(capability_ids) == len(DEFAULT_CAPABILITIES)


def test_prompt_model_keeps_prompt_separate_from_task():
    task = BenchmarkTask(
        id="task",
        version="1.0",
        category="coding",
        title="Task",
        prompt_template_id="template",
    )
    template = PromptTemplate(
        id="template",
        version="1.0",
        name="Template",
        template="Hello {name}",
    )
    prompt_version = PromptVersion(
        id="template_v1",
        version="1.0",
        prompt_template_id=template.id,
    )
    prompt = Prompt(
        task_id=task.id,
        prompt_template_id=template.id,
        prompt_version_id=prompt_version.id,
        text="Hello CareerHub",
    )

    assert not hasattr(task, "prompt")
    assert task.prompt_template_id == "template"
    assert prompt.text == "Hello CareerHub"


def test_generate_models_are_generic():
    prompt = Prompt(
        task_id="task",
        prompt_template_id="template",
        prompt_version_id="v1",
        text="Prompt",
    )
    request = GenerateRequest(
        model_name="model",
        prompt=prompt,
        settings={"temperature": 0.2},
    )
    result = GenerateResult(
        request=request,
        response_text="response",
    )
    model = ModelInfo(
        id="model",
        version="1.0",
        provider_id="provider",
        name="model",
    )

    assert result.request.model_name == "model"
    assert model.provider_id == "provider"


def test_plugin_registry_registers_all_plugin_types():
    registry = PluginRegistry()

    registry.register_provider("provider", DummyProvider)
    registry.register_suite("suite", DummySuite)
    registry.register_telemetry("telemetry", object)
    registry.register_archive("archive", object)
    registry.register_reporter("reporter", object)
    registry.register_evaluator("evaluator", object)
    registry.register_judge("judge", object)
    registry.register_capability("coding", object)

    assert registry.get("providers", "provider") is DummyProvider
    assert registry.get("suites", "suite") is DummySuite
    assert registry.list("capabilities") == ["coding"]


def test_interfaces_accept_structural_implementations():
    assert isinstance(DummySuite(), BenchmarkSuite)
    assert isinstance(DummyProvider(), ModelProvider)


def test_benchmark_pipeline_documents_target_flow():
    pipeline = BenchmarkPipeline()

    assert pipeline.steps == (
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


def test_openllmbench_module_entrypoint():
    result = subprocess.run(
        [sys.executable, "-m", "openllmbench"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "OpenLLMBench Foundation V1" in result.stdout
