# Documentation Audit

Date: 2026-07-11

Scope: **Historical private-development audit**, before the public export and
subsequent fixes. Findings and counts below describe that earlier snapshot;
they are not current public-release assertions. For current behavior see
[Architecture](architecture.md), [Features](features.md) and the README.

## Summary

The repository contains a broad local CareerHub prototype plus a growing CompanyHub module and an experimental OpenLLMBench foundation. The code supports profile handling, job loading, skill extraction, unknown skill review, job scoring, application package generation, company source management, company evidence extraction, company knowledge drafts and local Ollama integration.

Several features are implemented only as local prototypes or foundations. The previous draft documentation described some planned ideas as if they were production-ready and did not mention several implemented CompanyHub and validation components.

## Evidence Base

Key code areas reviewed:

- Streamlit entry point: `src/jobagent/ui/streamlit_app.py`
- Profile UI and review queue: `src/jobagent/ui/profile_tab.py`
- Job UI and ranking: `src/jobagent/ui/jobs_tab.py`
- Application package UI: `src/jobagent/ui/application_tab.py`
- CompanyHub UI: `src/jobagent/ui/company_tab.py`
- Job scoring: `src/jobagent/services/scorer.py`, `src/jobagent/models/score_result.py`
- Job loading: `src/jobagent/services/job_service.py`, `src/jobagent/sources/*.py`, `config/sources.yaml`
- Skill workflows: `src/jobagent/services/unknown_skill_service.py`, `skill_candidate_evaluator.py`, `skill_candidate_canonicalizer.py`, `review_queue_service.py`
- CompanyHub workflows: `company_fetch_service.py`, `company_analysis_pipeline.py`, `company_evidence_service.py`, `company_knowledge_builder.py`, `company_knowledge_review_service.py`, `company_profile_match_service.py`
- Document processing: `document_parser.py`, `document_processing_service.py`
- Application export: `application_html_service.py`, `application_pdf_service.py`, `application_package_service.py`
- LLM integration: `application_service.py`, `ollama_client.py`, `ollama_provider.py`
- Tests: root-level `test_*.py` files.

## Fully Implemented

- Streamlit app with profile, jobs, CompanyHub and application tabs (`streamlit_app.py`).
- Profile preferences in session state and CSV import/export (`profile_tab.py`, `skill_profile_io.py`, `test_skill_profile_io.py`).
- Job loading from JSON, RSS, Bundesagentur and Remotive sources (`job_service.py`, `sources/*.py`, `config/sources.yaml`).
- Profile-aware source query generation for Bundesagentur and Remotive (`profile_search_query_service.py`, `job_service.py`).
- Job score components for role, work model, salary, career, employer, skills, competencies and role mismatch (`scorer.py`, `score_result.py`, `test_role_mismatch_penalty.py`, `test_competency_score.py`).
- Unknown skill detection, LLM evaluation, canonicalization, candidate typing and review queue persistence (`unknown_skill_service.py`, `skill_candidate_evaluator.py`, `skill_candidate_canonicalizer.py`, `review_queue_service.py`).
- Recommendation snapshots, outcomes and validation summary/report foundation (`recommendation_snapshot_service.py`, `recommendation_outcome_service.py`, `validation_service.py`, `validation_report_service.py`).
- HTML and ZIP application package generation (`application_html_service.py`, `application_package_service.py`).
- Final PDF package generation when a real HTML-to-PDF renderer is available, with PDF/image attachment merging (`application_pdf_service.py`, `test_application_pdf_service.py`).
- CompanyHub SQLite repository, tracked companies, sources, documents, relationships and dashboard foundation (`company_repository.py`, `companyhub_db_service.py`, `company_tab.py`, corresponding tests).
- Company source fetching and raw document storage (`company_fetch_service.py`, `test_company_fetch_service.py`).
- Company evidence extraction and knowledge draft builder (`company_evidence_service.py`, `company_analysis_pipeline.py`, `company_knowledge_builder.py`).
- Company profile match foundation with mission, domain, technology, work model, KRITIS and exclusion weights (`company_profile_match_service.py`, `config/company_matching/company_matching.yaml`, `test_company_profile_match_service.py`).

## Partially Implemented

- OCR support exists through `document_parser.py`, but it hardcodes local Windows paths for Tesseract and Poppler. `document_processing_service.py` uses OCR only as an adapter when PDF text extraction is insufficient.
- PDF import and text extraction are implemented, but scanned PDF quality depends on local OCR tooling.
- Company Match exists in two forms: job-aggregated company matching (`company_match_service.py`) and CompanyHub profile matching (`company_profile_match_service.py`). They are related but not yet unified.
- Company Knowledge uses rule-based evidence and optional LLM-reviewed drafts. There is no approval workflow that promotes drafts into authoritative production knowledge.
- Live job sources exist, but there is no scheduler or automatic recurring crawl.
- Application PDF export is robust only when WeasyPrint or wkhtmltopdf/pdfkit is available.

## Experimental

- OpenLLMBench and the `careerhub/` benchmark runner are experimental/foundation work, not the active CareerHub UI runtime.
- Candidate insight extraction and prioritization for initiative applications are heuristic and tested, but still prototype-level.
- Manual Example Technologies company profile is demo/test material.
- Company concept canonicalization is a foundation with seed YAML files, not a complete company taxonomy.
- Ollama knowledge draft review is optional and guarded by fallback behavior, but still requires human review.

## Planned Or Concept

- Full autonomous company crawler or scheduler.
- Automated regular reanalysis and notifications.
- Agent-based research, red-team or decision agents.
- Production dashboard analytics.
- Automatic taxonomy updates without human review.
- Production-ready legal qualification decisions.

## Previously Overstated Or Incorrect

- OCR was described too broadly. It exists, but depends on hardcoded local Tesseract/Poppler paths.
- CompanyHub was described as mostly planned. In code it already includes SQLite, sources, fetching, evidence, knowledge drafts, LLM review and a dashboard foundation.
- "Live job sources" were not qualified. They exist through configured sources, but not as scheduled crawling.
- "Final PDF export" was too broad. It depends on a real HTML-to-PDF renderer.
- "Contextual resume" should be described as LLM-generated draft text, not a verified CV builder.
- Qwen support should be described as local Ollama model usage. Some code paths default to `qwen3:30b`; model availability is local-machine dependent.

## Missing Documentation

- CompanyHub source fetch, document, evidence and knowledge draft pipeline.
- Company pipeline inspector.
- Company profile matching weights and safe config fallback.
- Recommendation snapshots, outcomes and validation report foundation.
- Role mismatch penalty for job scoring.
- CSV profile preference import/export.
- OpenLLMBench should be documented separately as experimental/foundation, not as the main CareerHub product.

## Privacy And Publication Risks

- `data/` contains runtime files such as `companyhub.db`, `review_queue.json`, recommendation snapshots and outcomes. These should not be public by default.
- `benchmarks/outputs/` contains full prompt/response benchmark output and may include generated sensitive content.
- `logs/` may contain LLM prompts or application generation debug details.
- `src/jobagent/services/document_parser.py` and `src/jobagent/test_ocr.py` contain local absolute Windows tool paths.
- Some tests contain real-looking personal/demo names and Example Technologies application examples. These should be reviewed before publication.
- `.gitignore` was missing several runtime-data exclusions and has been expanded.

## Open Points

- Decide whether demo company profiles under `data/company_profiles/` are public-safe or should move to `examples/`.
- Replace hardcoded OCR paths with configuration before public release.
- Review all benchmark outputs before publishing or exclude them permanently.
- Clarify whether root documentation should focus only on CareerHub or include OpenLLMBench as a separate subproject.
