# ADR 0003: Prompt Is Not Task

## Status

Accepted

## Context

Prompt wording changes frequently. Task identity should not change every time a
prompt is improved. Without separation, comparing runs over time becomes
ambiguous.

## Decision

Tasks reference `prompt_template_id`. Prompt text lives in prompt templates and
prompt versions.

## Alternatives

- Store prompt text directly in every task.
- Store prompts only in external files without version models.
- Treat prompt changes as task changes.

## Consequences

Prompt iteration becomes trackable. Multiple prompt versions can target the same
task. The data model is slightly more complex but more reproducible.

