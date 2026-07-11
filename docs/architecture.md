# Architecture

## Overview

CareerHub is a local Streamlit application with service-oriented Python modules under `src/jobagent`. The architecture separates UI, services, repositories, models and source adapters.

Primary entry point:

- `src/jobagent/ui/streamlit_app.py`

Main tabs:

- Profile creation and skill review
- Job matching
- CompanyHub
- Application package generation
- Mail/send placeholder

## Component Status

### Streamlit UI

Status: **Implemented**

Files:

- `src/jobagent/ui/profile_tab.py`
- `src/jobagent/ui/jobs_tab.py`
- `src/jobagent/ui/company_tab.py`
- `src/jobagent/ui/application_tab.py`
- `src/jobagent/ui/streamlit_app.py`

The UI manages profile uploads, skill review, job results, CompanyHub workflows and application package exports.

### Document Processing

Status: **Partially implemented**

Files:

- `src/jobagent/services/document_parser.py`
- `src/jobagent/services/document_processing_service.py`
- `src/jobagent/models/document_processing_result.py`

Supported inputs include HTML, PDF, DOCX, Markdown and plain text. PDF text extraction uses `pypdf`. OCR is available through a Tesseract/Poppler adapter, but the current OCR helper contains local Windows paths and is not portable without configuration.

### Skill Extraction And Review Queue

Status: **Implemented**

Files:

- `src/jobagent/services/unknown_skill_service.py`
- `src/jobagent/services/skill_candidate_evaluator.py`
- `src/jobagent/services/skill_candidate_canonicalizer.py`
- `src/jobagent/services/skill_candidate_domain_service.py`
- `src/jobagent/services/review_queue_service.py`
- `src/jobagent/services/skill_registry_service.py`
- `src/jobagent/models/skill_candidate.py`
- `src/jobagent/models/skill_registry.py`

The pipeline detects unknown candidates, evaluates them through local Ollama where available, canonicalizes names, classifies candidate types and persists review items in a JSON-backed queue.

Candidate types include skills, roles, certifications, context terms, frameworks, regulations and unknowns.

Approved review items are persisted into the SQLite Skill Registry. The registry stores canonical names, display names, types, aliases, status, provenance and timestamps. It performs alias-based merge checks before insert and records type conflicts instead of merging across different types. Active registry entries are read by skill canonicalization and taxonomy loading, so new reviewed skills become available to matching without restarting the application.

`config/skill_taxonomy.yaml` remains a seed/import source. It is not the only runtime source of known skills once the registry has been initialized.

### Job Matching

Status: **Implemented**

Files:

- `src/jobagent/services/job_service.py`
- `src/jobagent/services/scorer.py`
- `src/jobagent/services/job_skill_service.py`
- `src/jobagent/services/competency_service.py`
- `src/jobagent/services/qualification_service.py`
- `src/jobagent/services/job_intelligence_service.py`
- `src/jobagent/models/score_result.py`

The job scorer uses role fit, work model, salary, career fit, employer fit, skill fit, competency fit and role mismatch penalties. Hard exclusions can remove jobs from normal ranking with a `-100` score.

### Job Sources

Status: **Implemented**

Files:

- `src/jobagent/sources/json_source.py`
- `src/jobagent/sources/rss_source.py`
- `src/jobagent/sources/bundesagentur_source.py`
- `src/jobagent/sources/remotive_source.py`
- `config/sources.yaml`

Configured live sources can be enabled or disabled. Profile-aware queries are applied to Bundesagentur and Remotive source configs.

There is no scheduler. Fetching happens when the UI/job workflow loads results.

### Application Generation And Export

Status: **Partially implemented**

Files:

- `src/jobagent/services/application_service.py`
- `src/jobagent/services/application_html_service.py`
- `src/jobagent/services/application_pdf_service.py`
- `src/jobagent/services/application_package_service.py`
- `src/jobagent/ui/application_tab.py`

CareerHub can generate cover letters, context resume text and initiative letters using local Ollama. HTML and ZIP exports are implemented. Full PDF export requires WeasyPrint or wkhtmltopdf/pdfkit; selected PDF/image attachments can be merged through `pypdf`.

### CompanyHub

Status: **Implemented / Experimental**

Files:

- `src/jobagent/repositories/company_repository.py`
- `src/jobagent/services/company_fetch_service.py`
- `src/jobagent/services/company_analysis_pipeline.py`
- `src/jobagent/services/company_evidence_service.py`
- `src/jobagent/services/company_knowledge_builder.py`
- `src/jobagent/services/company_knowledge_review_service.py`
- `src/jobagent/services/company_profile_match_service.py`
- `src/jobagent/services/company_pipeline_inspector.py`
- `src/jobagent/ui/company_tab.py`

CompanyHub includes tracked companies, sources, source fetching, document storage, evidence extraction, canonical company concepts, knowledge drafts, optional Ollama draft review and profile matching.

It is still a local prototype. It does not include a production crawler or automatic external research agent.

### LLM Integration

Status: **Implemented locally, environment-dependent**

Files:

- `src/jobagent/services/application_service.py`
- `src/jobagent/services/skill_candidate_evaluator.py`
- `src/jobagent/services/ollama_client.py`
- `src/jobagent/services/ollama_provider.py`

The application uses local Ollama. Some CareerHub paths default to `qwen3:30b`. CompanyHub knowledge review can list local Ollama models and use a selected model where available.

### OpenLLMBench

Status: **Experimental / Concept foundation**

Files:

- `careerhub/`
- `openllmbench/`
- `benchmarks/`
- `datasets/`

This is benchmark framework work inside the repository. It is not the primary CareerHub application runtime.

## Data Flow

```text
Profile / job / company source
        |
        v
Document loading and text extraction
        |
        v
Rule-based extraction and optional local LLM evaluation
        |
        +--> Human review queue for uncertain skill candidates
        |        |
        |        v
        |   SQLite Skill Registry
        |
        v
Scoring, matching or knowledge draft building
        |
        v
Explainability in UI and optional application package export
```

## Configuration

CareerHub prefers configuration for profile, scoring, source and company matching behavior. Several services include internal fallbacks for missing or invalid config, for example company match scoring and company profile matching.
