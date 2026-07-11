# Roadmap

## Phase 1: CareerHub MVP

Status: **Implemented**

- Streamlit application shell
- Profile preferences
- Skill extraction and review queue
- Job source loading
- Job scoring
- Local Ollama application text generation
- HTML and ZIP application package export

## Phase 2: Quality And Governance

Status: **Partially implemented**

- Candidate canonicalization
- Candidate typing
- Review queue deduplication
- Confidence values
- Persistent SQLite Skill Registry
- Human-review approval flow into persistent skills and aliases
- Idempotent taxonomy seed migration
- Skill-based scoring
- Competency and qualification explainability
- Recommendation snapshots and outcome events
- Validation report foundation

Remaining:

- broader regression test coverage
- richer taxonomy curation UI and export workflow
- public-safe demo data cleanup

## Phase 3: CompanyHub

Status: **Implemented foundation / Experimental**

Implemented:

- SQLite repository
- recommended and tracked companies
- company sources
- manual fetch workflow
- company documents
- evidence extraction
- knowledge drafts
- optional Ollama draft review
- pipeline inspector
- company profile matching

Remaining:

- approval workflow for knowledge drafts
- stronger evidence extraction
- better public demo dataset
- clearer separation between job-aggregated Company Match and CompanyHub profile match

## Phase 4: Application Package Maturity

Status: **Partially implemented**

Implemented:

- HTML package
- ZIP package
- final PDF when renderer is available
- attachment overview and merge pipeline

Remaining:

- portable renderer setup documentation
- more robust OCR/PDF attachment handling
- final visual QA across environments

## Phase 5: Automation

Status: **Planned**

- scheduled job refresh
- scheduled company source refresh
- change detection
- notification workflow
- automatic reanalysis after source changes

## Phase 6: OpenLLMBench

Status: **Experimental / Concept foundation**

Implemented foundations:

- benchmark runner under `careerhub/`
- OpenLLMBench package skeleton
- provider, judge, evaluation, dataset and SDK foundations

Remaining:

- migration from CareerHub benchmark runner
- standalone CLI
- stable plugin API
- dashboard or report UI

## Long-Term Concepts

Status: **Concept**

- agent-based research workflows
- red-team review agents
- personal career memory
- market monitoring
- broader company strategy assistant
