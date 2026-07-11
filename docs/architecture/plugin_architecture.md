# Plugin Architecture

OpenLLMBench uses plugins to keep the core small and reusable.

## Plugin Types

- Provider
- Archive
- Telemetry
- Reporter
- Evaluator
- Judge
- BenchmarkSuite
- CapabilityProvider

## Provider

Providers connect OpenLLMBench to model runtimes. Examples:

- Ollama
- LM Studio
- vLLM
- llama.cpp
- cloud APIs

## Archive

Archive plugins index benchmark outputs. DuckDB is the first target because it
is local, queryable and easy to distribute as a single file.

## Telemetry

Telemetry plugins collect contextual data such as system health, token metrics,
hardware state and progress events.

## Reporter

Reporters transform run artifacts into Markdown, CSV, HTML or other formats.

## Evaluator

Evaluators check structured behavior without subjective judging.

## Judge

Judges provide optional review. A judge can be human, LLM-based or a hybrid
workflow.

## BenchmarkSuite

Suites define domain tasks. CareerHub is the first planned suite.

