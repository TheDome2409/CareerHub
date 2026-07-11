# ADR 0005: DuckDB Archive

## Status

Accepted for first archive backend

## Context

Benchmark runs produce JSON, CSV and Markdown artifacts. Over time, comparing
models and runs across many files becomes inconvenient. A local analytics index
is useful, but running a server database would be too heavy for the project
phase.

## Decision

Use DuckDB as the first archive backend.

## Alternatives

- SQLite
- PostgreSQL
- Parquet-only storage
- No archive database

## Consequences

DuckDB provides local SQL analytics in a single file. It is optional and should
not replace raw JSON/CSV artifacts. The project must handle missing DuckDB
gracefully.

