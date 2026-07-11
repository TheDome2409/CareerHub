from pathlib import Path


REQUIRED_DOCS = [
    "README.md",
    "ROADMAP.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "CODE_OF_CONDUCT.md",
    "docs/architecture/overview.md",
    "docs/architecture/benchmark_pipeline.md",
    "docs/architecture/plugin_architecture.md",
    "docs/architecture/telemetry.md",
    "docs/architecture/archive.md",
    "docs/philosophy.md",
    "docs/development/README.md",
    "docs/benchmark_suites/README.md",
    "docs/providers/README.md",
    "docs/tutorials/quick_start.md",
    "docs/tutorials/create_benchmark_suite.md",
    "docs/tutorials/create_provider.md",
    "docs/tutorials/create_judge.md",
    "docs/tutorials/create_evaluator.md",
    "docs/decisions/0001-project-name.md",
    "docs/decisions/0002-plugin-architecture.md",
    "docs/decisions/0003-prompt-separation.md",
    "docs/decisions/0004-capability-model.md",
    "docs/decisions/0005-duckdb.md",
    "docs/decisions/0006-local-first.md",
]


def test_required_openllmbench_docs_exist():
    missing = [path for path in REQUIRED_DOCS if not Path(path).exists()]

    assert missing == []


def test_readme_references_existing_documents():
    readme = Path("README.md").read_text(encoding="utf-8")
    referenced = [
        "docs/architecture/overview.md",
        "docs/architecture/benchmark_pipeline.md",
        "docs/architecture/plugin_architecture.md",
        "docs/architecture/telemetry.md",
        "docs/architecture/archive.md",
        "docs/benchmark_suites/README.md",
        "docs/providers/README.md",
        "docs/tutorials/create_benchmark_suite.md",
        "docs/tutorials/create_provider.md",
        "docs/tutorials/quick_start.md",
        "docs/tutorials/create_evaluator.md",
        "docs/tutorials/create_judge.md",
        "docs/philosophy.md",
        "ROADMAP.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "CODE_OF_CONDUCT.md",
    ]

    for path in referenced:
        assert path in readme
        assert Path(path).exists()


def test_adrs_have_required_sections():
    for path in Path("docs/decisions").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert "## Status" in text
        assert "## Context" in text
        assert "## Decision" in text
        assert "## Alternatives" in text
        assert "## Consequences" in text
