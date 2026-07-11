import subprocess
import sys

from openllmbench.core.datasets import load_dataset, load_dataset_task
from openllmbench.sdk import (
    BenchmarkSuiteBuilder,
    CapabilityBuilder,
    DatasetBuilder,
    PromptBuilder,
    TaskBuilder,
)


def test_capability_builder_deduplicates():
    capabilities = CapabilityBuilder().add("coding").add("coding").add("analysis").build()

    assert capabilities == ["coding", "analysis"]


def test_prompt_builder_writes_yaml(tmp_path):
    path = PromptBuilder(template_id="prompt").write(tmp_path / "prompt.yaml")

    assert path.exists()
    assert "template:" in path.read_text(encoding="utf-8")


def test_dataset_builder_writes_dataset_and_task(tmp_path):
    task = TaskBuilder(
        task_id="task",
        prompt_template="prompt",
        evaluation_profile="evaluation_profiles/coding.yaml",
        capabilities=["coding"],
    )
    DatasetBuilder(
        dataset_id="sdk_dataset",
        name="SDK Dataset",
        description="Dataset from SDK.",
    ).add_task(task).write(tmp_path / "sdk_dataset")

    dataset = load_dataset(tmp_path / "sdk_dataset")
    loaded_task = load_dataset_task(tmp_path / "sdk_dataset" / "tasks" / "task.yaml")

    assert dataset.id == "sdk_dataset"
    assert dataset.task_count == 1
    assert loaded_task.prompt_template == "prompt"


def test_benchmark_suite_builder_creates_full_scaffold(tmp_path):
    paths = BenchmarkSuiteBuilder(
        suite_name="My Suite",
        output_root=tmp_path,
        capabilities=["documentation"],
        author="Tester",
    ).build()

    assert paths["dataset"].exists()
    assert paths["task"].exists()
    assert paths["prompt"].exists()
    assert paths["readme"].exists()
    assert paths["docs"].exists()
    assert paths["tests"].exists()
    dataset = load_dataset(tmp_path / "my_suite")
    assert dataset.id == "my_suite"
    assert dataset.tasks[0].author == "Tester"


def test_create_suite_cli(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "openllmbench",
            "create-suite",
            "CLI Suite",
            "--output-root",
            str(tmp_path),
            "--capabilities",
            "coding",
            "analysis",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Created OpenLLMBench suite scaffold" in result.stdout
    assert (tmp_path / "cli_suite" / "dataset.yaml").exists()
    assert (tmp_path / "cli_suite" / "tasks" / "cli_suite_sample_task.yaml").exists()
    assert (tmp_path / "cli_suite" / "prompts" / "cli_suite_prompt_v1.yaml").exists()
