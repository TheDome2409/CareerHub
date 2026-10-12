# Product Owner Case Study

Status: **Implemented documentation**

This case study describes CareerHub as a product and delivery artifact. It is
intended for Product Owner, Technical Product Owner, Inhouse AI Consultant and
IT project-management conversations.

## Context

CareerHub addresses a fragmented career workflow:

- profile and skill analysis
- job matching
- company evaluation
- application text generation
- document export
- governance around uncertain AI outputs

The product challenge was not only to generate application text. The larger
problem was creating a traceable workflow in which profile data, job data,
company context and human review remain connected.

## Product Role

The project owner defined the product vision, prioritized increments, reviewed
outputs, approved release decisions and decided when to shift from feature work
to publication readiness.

AI tools assisted with implementation, review and documentation work:

- Codex was used for code creation, refactoring, tests and reviews.
- Local LLM/Ollama integration was used as an optional runtime capability inside
  the product.
- Human review remained responsible for prioritization, product decisions,
  acceptance, tests and release readiness.

This repository does not claim that all code was manually written. It documents
an AI-assisted engineering workflow with human product ownership.

## Key Decisions

### Local LLMs Instead Of Mandatory Cloud LLMs

Sensitive career data should not require an external cloud model. CareerHub uses
local Ollama workflows where LLM support is needed and keeps deterministic
workflows usable without a model.

### Human Review Instead Of Automatic Knowledge Changes

Unknown skills may be suggested by rules or LLMs, but they should not
automatically become active profile knowledge. The review queue and registry
workflow keep approval explicit.

### Registry-First Persistent Skill Knowledge

The Persistent Skill Registry uses SQLite so approved skills and aliases survive
restarts and are available to matching immediately. YAML seeds, keywords and
alias fallbacks remain runtime inputs; SQLite-only lookup is future work.

### YAML As Seed And Import Source

YAML remains useful for examples, taxonomy seeds and configuration. It is not
treated as the only runtime source once reviewed skill knowledge exists.

### AGPLv3 License

AGPLv3 was selected to keep modified network-deployed versions transparent and
source-available.

### New Public Repository History

The public candidate uses a fresh Git history rather than publishing private
development history. This protects private data, local artifacts and unfinished
experiments.

### Persistent Skill Registry Before Public Release

Skill persistence was prioritized because the Unknown Skill workflow otherwise
ended before becoming durable product value.

### CompanyHub As Foundation

CompanyHub was intentionally released as a foundation: sources, documents,
evidence, drafts and matching dimensions exist, but no production crawler or
automated research agent is claimed.

### v0.1.0 As Portfolio Release

The release goal is a transparent public portfolio candidate, not a production
SaaS launch.

## Prioritization Examples

- Skill persistence was completed before public release because it closed a core
  workflow gap.
- Agent workflows were deferred because deterministic foundations and review
  controls were more important for v0.1.0.
- Public-readiness, privacy scans, licensing and documentation were prioritized
  before adding more features.
- Bugs and regressions were handled after feature completion through focused
  tests, smoke checks and release-gate runs.
- CompanyHub source fetching and evidence inspection were released as
  foundations rather than overextending into a production crawler.

## Quality And Governance

CareerHub uses several quality and governance practices:

- pytest-based regression tests
- Streamlit import/bootstrap tests
- CI workflow
- `compileall` checks
- markdown link checks during release preparation
- secret and privacy scans
- `.gitignore` separation of runtime/private data
- dependency license inventory
- third-party notices
- security and support documentation
- release notes
- due-diligence documentation

## Outcome

The public candidate before pre-publication remediation was assessed as a
portfolio prototype, with the following recorded checks and capabilities:

- `324 passed, 3 skipped`
- AGPLv3 license
- Persistent Skill Registry
- Human-in-the-Loop Review Queue
- CompanyHub Foundation
- local LLM integration paths
- OpenLLMBench Foundation
- synthetic public examples
- reproducible release checks

It remains a local prototype, not a production HR product.

## Lessons Learned

- Product value increased when uncertain concepts had a lifecycle: detected,
  reviewed, persisted and reused.
- Explainability should be designed into the workflow, not added only at the
  report layer.
- Local-first AI workflows still need governance: prompts, review steps,
  persistence rules and privacy boundaries.
- Open-source readiness is product work. Documentation, licensing, testability
  and data hygiene are part of the release.
- Foundations should be named honestly. CompanyHub and OpenLLMBench are valuable
  foundations, but not yet mature standalone products.
