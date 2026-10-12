# Product Journey

Status: **Implemented documentation**

This document describes the product evolution of CareerHub at a product level.
It intentionally avoids invented dates, usage numbers or unsupported chronology.
The sequence reflects the implemented and documented project shape in the public
v0.1.0 candidate.

## Starting Problem

Application workflows are often fragmented. Job analysis, profile maintenance,
company evaluation and application-document preparation tend to happen in
separate tools. That fragmentation makes it difficult to keep skills,
preferences, evidence and generated documents consistent.

Classic keyword matching also has limits. It can find obvious term overlap, but
it often underrepresents personal preferences, work model, travel expectations,
qualification signals, lifestyle constraints and the user's actual career
intent.

## First Product Assumption

The first product assumption behind CareerHub was that a local application
assistant can connect analysis and document generation without forcing sensitive
profile data into external services.

The intended role of AI was supportive rather than autonomous:

- local processing where possible
- deterministic extraction and scoring before generative output
- visible score components instead of black-box recommendations
- human review before uncertain skills become trusted knowledge

## MVP

The early MVP focused on connecting profile material, job descriptions and
application output in one local workflow.

Implemented MVP-level capabilities include:

- document import
- PDF text extraction and optional OCR path
- profile analysis
- job analysis
- skill detection
- explainable job matching
- cover-letter and application-package generation

These functions established the basic loop:

```text
Profile + job data -> analysis -> matching -> explainability -> application draft
```

## Product Development

### Unknown Skill Candidates

As soon as profile and job text were analyzed, new or domain-specific terms
appeared that were not part of the original taxonomy. Treating every unknown
term as noise would lose useful information. Treating every term as a trusted
skill would create noise in matching.

Unknown Skill Candidates were introduced to keep that middle state explicit.

### Human-in-the-Loop Review Queue

LLM evaluation can help classify or explain unknown terms, but it can also be
uncertain or wrong. The review queue separates suggestion from acceptance.
Candidates can be pending, approved or rejected, and the human reviewer remains
responsible for the decision.

### Canonicalization And Typing

Skill extraction quickly needs more than raw strings. Canonicalization and
typing were added so that aliases, roles, certifications, frameworks,
regulations and context terms can be handled more consistently.

This reduced duplicate concepts and made later persistence possible.

### CompanyHub Foundation

Job fit alone was not sufficient. Company context, mission, working model,
technology domains and infrastructure relevance also influence whether an
opportunity is attractive.

CompanyHub was introduced as a foundation for:

- tracked companies
- company sources
- fetched documents
- evidence snippets
- knowledge drafts
- pipeline inspection

It is intentionally not a full crawler or company intelligence product in
v0.1.0.

### Mission, Domain, Technology, Work-Model And KRITIS Fit

Company profile matching added dimensions that are not purely job-description
based:

- personal mission
- business domains
- technology overlap
- preferred and acceptable work models
- critical-infrastructure affinity
- exclusions

This made company evaluation closer to career-fit reasoning rather than only
role-term matching.

### OpenLLMBench Foundation

Local LLM workflows introduced a practical question: which local models are
useful for the specific tasks CareerHub asks them to perform?

The benchmark foundation was added to make local model runs more reproducible,
with task metadata, telemetry, progress files and future evaluation hooks. It is
experimental and not the main CareerHub runtime.

### Persistent Skill Registry V1

The review queue alone was not enough. Approved skills needed a persistent
durable runtime storage so that new knowledge survives restarts and immediately
affects matching.

The SQLite Skill Registry was therefore prioritized before the public release.
The current architecture is registry-first: SQLite stores reviewed skills and
aliases, while YAML still supplies seed migration, keywords and alias fallbacks.
An exclusive SQLite runtime is future work; see ADR 0003.

### Open-Source Release Process

Preparing v0.1.0 for publication required product and governance work in
addition to implementation:

- public-safe synthetic examples
- removal of runtime artifacts
- secret and privacy scans
- AGPLv3 licensing
- dependency inventory
- related-work documentation
- release notes
- a new public Git history without private development history

## Lessons Learned

- Fachlicher Fit alone is not enough for useful career decisions. Work model,
  travel, on-call expectations, qualification requirements and identification
  with the product or mission can matter just as much.
- Uncertain AI output needs traceable review processes. A suggestion should not
  automatically become active profile knowledge.
- Runtime data and public demo data must be strictly separated.
- A productive workflow needs a persistent, unambiguous source of truth for
  accepted skills and aliases.
- Company context needs evidence and explainability before it can responsibly
  influence decisions.

## Deliberately Deferred Functions

### Full Agent Platform

Status: **Planned / Concept**

Agent workflows were deferred because v0.1.0 needed deterministic foundations,
review queues and public-safe governance first.

### Automatic Scheduler Or Crawler

Status: **Planned**

Scheduled refresh and crawling would add reliability, source governance and
privacy questions. Manual fetch and inspection are enough for the initial
foundation.

### Comprehensive Company-Intelligence Sources

Status: **Planned / Concept**

CompanyHub currently stores sources, documents, evidence and drafts. A broader
company intelligence layer requires stronger source handling, deduplication,
review workflows and legal review.

### Full Registry Management UI

Status: **Planned**

The persistent registry exists and is integrated with review decisions. A richer
management UI was deferred to keep the public release focused and testable.

### Public Demo

Status: **Planned**

The repository includes synthetic examples and screenshot guidance, but no
hosted public demo. A demo should only be published after privacy-safe
screenshots and installation checks are complete.

### Productive Multi-User Operation

Status: **Concept**

CareerHub v0.1.0 is local-first and single-user oriented. Multi-user operation
would require authentication, authorization, deployment architecture, data
isolation and security hardening beyond this release.
