# ADR 0006: Local First

## Status

Accepted

## Context

Many benchmark tasks may include private documents, proprietary code or
workflow-specific prompts. Requiring cloud services would limit adoption and
create privacy concerns.

## Decision

OpenLLMBench is local-first. Local providers such as Ollama are first-class.
Remote providers can be added later through the provider interface.

## Alternatives

- Cloud-first provider support.
- Only support one local runtime.
- Leave execution location undefined.

## Consequences

Users can run private benchmarks without uploading data. Local hardware
telemetry becomes important. Provider abstractions must remain flexible enough
for future remote systems.

