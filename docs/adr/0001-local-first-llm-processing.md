# ADR 0001: Local-First LLM Processing

Status: **Accepted**

## Context

CareerHub handles profile, application and company-context data that may be
sensitive. Some workflows benefit from LLM support, but requiring a cloud LLM
would weaken the local-first privacy goal.

## Decision

CareerHub supports optional local LLM workflows through Ollama. Deterministic
parts of the product should remain usable without a local model.

## Consequences

- Users can keep sensitive workflows on their own machine.
- Model availability, speed and quality depend on the local environment.
- The project must document model-license responsibility clearly.
- LLM output remains assistive and subject to human review.

## Alternatives Considered

- Mandatory cloud LLM API: simpler model access, weaker privacy posture.
- No LLM integration: simpler architecture, less useful drafting/evaluation
  support.
- Multiple provider abstraction first: more flexible, too broad for v0.1.0.
