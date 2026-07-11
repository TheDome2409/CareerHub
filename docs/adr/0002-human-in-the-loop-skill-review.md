# ADR 0002: Human-in-the-Loop Skill Review

Status: **Accepted**

## Context

Profile and job documents contain unknown terms. Some are valuable skills,
certifications, frameworks or regulations. Others are context, noise or
ambiguous phrases. Automatically activating every detected or LLM-approved term
would reduce matching quality.

## Decision

Unknown skill candidates must pass through a review queue before they become
trusted skill knowledge. LLM evaluation may provide confidence and rationale,
but it does not automatically activate skills or profile weights.

## Consequences

- Skill governance is explicit.
- Users can accept, reject, merge or adjust candidates.
- The workflow is slower than full automation, but safer and more explainable.
- Review queue persistence becomes part of the product model.

## Alternatives Considered

- Automatically activate positive LLM evaluations: faster, but prone to
  hallucinated or noisy skills.
- Ignore unknown terms: safer, but loses emerging or domain-specific knowledge.
- Store all unknown terms as inactive text only: traceable, but does not close
  the loop into matching.
