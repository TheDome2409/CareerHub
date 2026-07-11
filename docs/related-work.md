# Related Work

Status: **Implemented documentation**

This page places CareerHub in context. It is not a claim of scientific novelty
or uniqueness. The goal is to be transparent about overlap with existing tools
and to describe what CareerHub contributes as an integrated local prototype.

Sources were checked during the v0.1.0 public launch preparation. URLs are
included so readers can verify details against the upstream projects.

## Resume Builders And Application Tools

### Reactive Resume

- Purpose: open-source resume builder with self-hosting and PDF/export-oriented
  workflows.
- License: MIT, according to the GitHub repository metadata.
- Source: <https://github.com/AmruthPillai/Reactive-Resume>
- Overlap: resume construction, privacy-oriented positioning and application
  document generation.
- Difference: CareerHub is not primarily a resume design product. It focuses on
  profile-to-job/company matching, skill governance, local LLM-assisted drafts,
  explainability and company evidence foundations.

### OpenResume

- Purpose: open-source resume builder and resume parser.
- License: AGPL-3.0, according to the GitHub repository metadata.
- Source: <https://github.com/xitanggg/open-resume>
- Overlap: resume parsing/building and open-source career tooling.
- Difference: CareerHub uses resume/profile documents as one input into a wider
  local workflow: unknown-skill review, persistent skill registry, job scoring,
  company analysis foundations and application-package export.

### Resume Matcher

- Purpose: AI-assisted workflow for tailoring resumes, cover letters and related
  application material.
- License: Apache-2.0, according to the GitHub repository metadata.
- Source: <https://github.com/srbhr/Resume-Matcher>
- Overlap: resume/job comparison, local/remote LLM-assisted application content,
  PDF and cover-letter workflows.
- Difference: CareerHub emphasizes deterministic score components, human review
  of new skills, a persistent skill registry, CompanyHub foundations and a
  local-first Streamlit prototype rather than a broader resume-tailoring
  platform.

## Job And Skill Matching

### ESCO

- Purpose: European multilingual classification of skills, competences,
  qualifications and occupations.
- License/source status: European Commission public classification; license and
  reuse terms should be checked from the ESCO portal before redistribution.
- Source: <https://esco.ec.europa.eu/en/about-esco/what-esco>
- Overlap: skill/occupation taxonomy concepts, aliases and matching language.
- Difference: CareerHub does not ship ESCO data. It uses small local taxonomy
  seed files plus a SQLite Skill Registry. ESCO is a reference point for what a
  mature skill taxonomy can look like.

### Resume-job matching research

- Purpose: research on matching resumes to jobs through keyword, embedding,
  contrastive, reranking or explainable systems.
- Example sources:
  - ConFit: <https://arxiv.org/abs/2401.16349>
  - ConFit v2: <https://arxiv.org/abs/2502.12361>
  - JobMatchAI: <https://arxiv.org/abs/2603.14558>
- Overlap: matching people to jobs, skill generalization and explainability.
- Difference: CareerHub v0.1.0 is not an ML-trained ranking system. It uses
  local deterministic scoring, heuristic extraction, optional Ollama assistance
  and visible score components.

## Local LLM Applications

### Ollama

- Purpose: local model serving, model management and REST/Python access for open
  models.
- License: MIT for the Ollama project, according to the GitHub repository
  metadata. Individual model licenses vary.
- Source: <https://github.com/ollama/ollama>
- Overlap: CareerHub uses Ollama as the optional local LLM backend for skill
  candidate evaluation, application text generation, knowledge draft review and
  benchmark experiments.
- Difference: CareerHub is not a model runtime. It consumes a local Ollama
  service and keeps model selection/user licensing outside the repository.

### RAG and document-assistant frameworks

- Examples: LangChain, LlamaIndex, Haystack and many Ollama community tools.
- Overlap: local document processing, LLM orchestration and explainable source
  context.
- Difference: CareerHub currently avoids a general RAG stack. Its document
  pipeline is deliberately narrow: extract/normalize text, derive evidence and
  keep human-readable traceability for matching and application workflows.

## Company Intelligence And Employer Matching

Many commercial and internal tools analyze employers through websites, reports,
reviews, news or firmographic data. CareerHub's CompanyHub foundation overlaps
with those ideas at the data-model level:

- companies
- sources
- fetched documents
- evidence snippets
- knowledge drafts
- relationships
- mission/domain/technology/work-model matching

CareerHub v0.1.0 does **not** include a production web crawler, scheduled
monitoring system, news intelligence product or external company-data provider.
It provides a local, inspectable foundation for future company evidence and
profile fit workflows.

## Benchmarking And Evaluation

### Language Model Evaluation Harness

- Purpose: framework for evaluating language models on many benchmark tasks.
- License: MIT, according to the GitHub repository metadata.
- Source: <https://github.com/EleutherAI/lm-evaluation-harness>
- Overlap: model benchmarking, reproducibility and task-based evaluation.
- Difference: CareerHub's benchmark runner and OpenLLMBench foundation focus on
  local Ollama models, portfolio-specific tasks, telemetry and future human
  evaluation. They are experimental foundations, not replacements for mature
  benchmark suites.

## What CareerHub Adds

CareerHub's independent contribution is the integration of several practical
career workflows into one local, inspectable prototype:

- **Implemented**: local-first processing for profiles, job data, company
  evidence and application documents.
- **Implemented**: combined profile, job and company workflow in a Streamlit UI.
- **Implemented**: persistent SQLite Skill Registry fed by human-approved
  unknown skill candidates.
- **Implemented**: Human-in-the-Loop Review Queue where LLM-evaluated unknown
  skills are suggestions, not automatically active profile skills.
- **Implemented**: controlled skill alias merge and conflict handling before new
  skills enter the registry.
- **Implemented**: deterministic job scoring with role, work model, salary,
  career, employer, skill, competency and role-mismatch components.
- **Implemented**: CompanyHub foundation for recommended/tracked companies,
  sources, documents, evidence, canonical concepts, knowledge drafts and
  pipeline inspection.
- **Implemented**: company profile match dimensions for mission, domains,
  technologies, work models, KRITIS affinity and exclusions.
- **Implemented**: explainable application-package context through candidate
  insights, company reports and attachment overview.
- **Partially implemented**: final PDF application packages, dependent on local
  HTML-to-PDF renderer availability.
- **Experimental**: local Ollama benchmarking and OpenLLMBench framework
  foundations.
- **Implemented**: public-safe split between runtime/private data and source
  code, with synthetic demo examples.

CareerHub does not claim scientific novelty, patentability, regulatory
compliance or global uniqueness.
