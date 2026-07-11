# OpenLLMBench Roadmap

This roadmap describes the intended evolution of OpenLLMBench from foundation
package to stable benchmark framework. Dates are intentionally omitted until the
project separates fully from the CareerHub runtime.

## v0.1 Foundation

Goal: establish the project shape without changing the existing CareerHub
benchmark.

Planned and current scope:

- package skeleton
- core interfaces
- versioned core models
- capability model
- prompt-template separation
- plugin registry foundation
- documentation foundation
- ADR foundation

Exit criteria:

- OpenLLMBench imports cleanly
- existing CareerHub benchmark remains unchanged
- documentation describes architecture and migration path

## v0.2 Providers

Goal: introduce provider plugins.

Planned scope:

- `ModelProvider` base contract hardened
- Ollama provider migrated behind the provider interface
- provider metadata model
- provider test fixtures
- provider-level error handling

Exit criteria:

- Ollama can run through OpenLLMBench provider abstractions
- legacy CareerHub CLI still works

## v0.3 Evaluation

Goal: add non-LLM evaluation foundations.

Planned scope:

- evaluator interface implementation
- structured result model
- rule-based evaluators
- schema and format checks
- benchmark-suite specific expected output contracts

Exit criteria:

- evaluators can run without judging quality subjectively
- evaluation artifacts are stored separately from raw outputs

## v0.4 Judge

Goal: introduce optional judge workflows.

Planned scope:

- judge interface implementation
- human-review friendly judge result model
- optional LLM-as-judge adapter
- rubric model
- judge prompt versioning

Exit criteria:

- judging is optional
- raw benchmark output remains unchanged
- judge outputs are auditable

## v0.5 Dashboard

Goal: provide visibility into runs.

Planned scope:

- read-only dashboard prototype
- progress state display
- metrics comparison
- archive browsing
- run detail pages

Exit criteria:

- dashboard reads existing JSON/CSV/DuckDB artifacts
- no dashboard dependency is required for CLI usage

## v1.0 Stable API

Goal: stabilize public APIs and artifact formats.

Planned scope:

- stable CLI
- stable provider interface
- stable suite interface
- stable archive schema
- migration notes for legacy CareerHub benchmark users
- public documentation complete enough for external contributors

Exit criteria:

- semantic versioning begins
- backward compatibility policy documented
- at least two benchmark suites and one provider are production-ready

## Future Ideas

- Parquet export
- MLflow integration
- Grafana/Prometheus exporters
- model cost tracking
- multi-node benchmark execution
- dataset cards for benchmark suites
- signed benchmark manifests
- benchmark result diffing
- regression detection
- prompt drift analysis
- human review queues
- plugin discovery through entry points

