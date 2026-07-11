# Telemetry

Telemetry captures what happened during a benchmark run.

It is not a quality judgment. It is context.

## Telemetry Categories

- token metrics
- timing metrics
- system health
- model metadata
- progress events
- provider raw metadata

## Why Telemetry Matters

Benchmark results can be affected by:

- memory pressure
- background CPU usage
- GPU contention
- model reloads
- prompt size
- token throughput
- disk or swap activity

Without telemetry, two runs can look comparable while being technically very
different.

## Design Rules

- Missing telemetry must not abort a run.
- Telemetry should be versioned.
- Raw provider metrics should be preserved.
- Derived metrics should be reproducible.
- Telemetry should be machine-readable.

