# Archive

The archive layer indexes benchmark artifacts for comparison over time.

## Source of Truth

JSON and CSV files remain the source of truth for a run. Archive databases are
analysis indexes built from those artifacts.

## DuckDB

DuckDB is the first archive backend because it is:

- local-first
- portable as a single file
- SQL-queryable
- suitable for analytics
- easy to use without a server

## Archive Responsibilities

- ingest run metadata
- ingest model metadata
- ingest task results
- ingest metrics
- support run listing
- support model comparison
- support run comparison

## Non-Goals

The archive does not judge quality, modify outputs or replace raw artifacts.

