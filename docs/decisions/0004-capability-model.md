# ADR 0004: Capability Model

## Status

Accepted

## Context

Benchmark suites often test abilities rather than simple categories. A coding
suite, architecture suite and security suite may overlap in reasoning,
documentation and long-context requirements.

## Decision

Introduce explicit capabilities with stable IDs, such as `coding`, `analysis`,
`documentation`, `architecture`, `security`, `reasoning`, `career_matching` and
`long_context`.

## Alternatives

- Use free-form tags only.
- Infer capabilities from task categories.
- Attach capabilities only to models.

## Consequences

Suites, tasks and models can refer to the same capability vocabulary. This helps
future reporting and suite composition. The vocabulary must be curated to avoid
becoming noisy.

