# Product Vision

Status: **Implemented documentation**

## Vision

CareerHub aims to be a local, transparent and human-centered career assistant
that helps users make more informed professional decisions.

It should connect profile understanding, job analysis, company context and
application preparation while keeping sensitive career data under the user's
control whenever possible.

## Target Audiences

CareerHub v0.1.0 is realistic about its audience:

- technically interested individual users
- applicants with a strong privacy preference
- developers and researchers exploring local LLM workflows
- product and engineering reviewers interested in explainable career tooling

It is currently **not** a production recruiting system, HR decision platform or
multi-user applicant tracking system.

## User Problems

- Job descriptions are often unstructured and difficult to compare.
- Application documents can become inconsistent across roles and companies.
- Matching scores are often opaque.
- Unknown or emerging competencies can be lost if they are not part of a fixed
  taxonomy.
- Personal work preferences such as remote/hybrid/onsite, travel, exclusions
  and salary targets are often underrepresented.
- Sensitive career data is frequently copied into external cloud tools without
  a clear review trail.

## Product Principles

- **Local first**: keep sensitive workflows local where practical.
- **Human in the loop**: suggestions are not final decisions.
- **Explainability over black box**: expose score components and evidence.
- **Configuration over hardcoding**: prefer explicit configuration and seed
  files over hidden assumptions.
- **Privacy by design**: separate runtime data from public code and examples.
- **Synthetic public examples**: public demos must not depend on private data.
- **Deterministic validation before generative output**: use structured
  extraction, scoring and review before asking an LLM to draft text.
- **No automatic final personnel decisions**: CareerHub assists; it does not
  decide.

## Non-Goals

- No fully automated application or hiring decision.
- No replacement for human career advice.
- No guaranteed legal, regulatory or professional qualification assessment.
- No production applicant tracking system.
- No autonomous sending of applications.
- No unattended learning from private data.
- No claim of scientific novelty or universal matching correctness.
