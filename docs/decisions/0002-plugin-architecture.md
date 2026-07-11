# ADR 0002: Plugin Architecture

## Status

Accepted

## Context

Different users will need different model providers, archives, telemetry
systems, benchmark suites and reporting formats. Hard-coding those concerns into
the runner would make the framework difficult to extend.

## Decision

OpenLLMBench will use a plugin architecture with registry entries for providers,
suites, telemetry, archives, reporters, evaluators, judges and capabilities.

## Alternatives

- A single monolithic runner.
- Separate scripts for every provider and suite.
- Dynamic discovery only, without an explicit registry.

## Consequences

The core remains small and easier to test. Plugins can evolve independently.
The cost is a slightly more formal interface layer.

