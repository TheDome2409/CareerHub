# Architecture Overview

OpenLLMBench is designed as a modular benchmark framework. Its core should know
how to orchestrate runs, but it should not know the details of a specific model
provider, benchmark domain, archive database or evaluation strategy.

## Layers

```text
CLI / API
↓
Runner
↓
Suite + Provider + Telemetry + Archive + Reporter
↓
Versioned Artifacts
```

The runner is responsible for sequencing work. Plugins are responsible for
domain-specific behavior.

## Core Concepts

- **BenchmarkSuite**: defines tasks and suite metadata.
- **BenchmarkTask**: defines what should be tested, but not the prompt text
  itself.
- **PromptTemplate**: stores reusable prompt structure.
- **PromptVersion**: records prompt evolution.
- **ModelProvider**: executes prompts against a model backend.
- **TelemetryProvider**: records runtime conditions and technical metrics.
- **ArchiveBackend**: indexes benchmark artifacts for comparison.
- **Evaluator**: computes deterministic or rules-based checks.
- **Judge**: performs subjective or rubric-based review.
- **Reporter**: renders human-readable or machine-readable reports.

## Compatibility Principle

The existing CareerHub benchmark remains the runtime implementation until the
migration is explicit. OpenLLMBench currently defines the future target shape.

