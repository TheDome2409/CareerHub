# Features

## Implemented

### Profile And Preferences

- Profile model with location, work model, salary, preferred roles, skills, certifications, career goals, interests, exclusions and employer preferences.
- GUI controls for salary targets, preferred/acceptable work models and hard exclusions.
- CSV export/import for skill rows and profile preference rows.
- Profile mission foundation generated from profile terms.

### Document Processing

- PDF text extraction with `pypdf`.
- OCR fallback path through Tesseract and Poppler adapter.
- HTML, DOCX, Markdown and text processing through the unified document processing service.
- Export text normalization for application-package rendering.

Status: **Partially implemented** because OCR requires local tools and hardcoded paths currently exist in helper code.

### Skill And Candidate Workflows

- Unknown skill candidate detection.
- Domain-aware term patterns for German professional terms.
- LLM-based unknown candidate evaluation through Ollama.
- Canonicalization and deduplication.
- Candidate typing for skill, role, certification, context, framework and regulation.
- Confidence values and source metadata.
- Persistent JSON review queue.
- Human status update for pending, approved and rejected candidates.
- Persistent SQLite Skill Registry as the runtime source of known skills.
- Human-approved review candidates can create a new skill, merge into an existing skill, add aliases or surface a type conflict for review.
- Active registry skills and aliases are available immediately to skill canonicalization, unknown-skill detection and job/profile skill matching.
- Idempotent seed migration from `config/skill_taxonomy.yaml` into the registry.

Status: **Implemented**

### Job Matching

- Loading jobs from configured JSON, RSS, Bundesagentur and Remotive sources.
- Profile-aware query generation.
- Job deduplication.
- Score components for role, work model, salary, career, employer, skill, competency and role mismatch.
- Hard exclusions.
- Qualification warnings.
- Job intelligence extraction for skills, competencies, qualification requirements and evidence requirements.
- Recommendation snapshots and outcome events.

Status: **Implemented**, with live source reliability dependent on external endpoints.

### Company Match And CompanyHub

- Aggregation of companies from loaded jobs for Company Match.
- Company Match report and initiative application context.
- Manual company profile loading for demo/test use.
- SQLite-backed CompanyHub repository.
- Recommended companies and tracked companies.
- Company sources and manual source fetch.
- Company documents, evidence extraction and knowledge drafts.
- Canonical company concepts from seed YAML files.
- Optional Ollama review of company knowledge drafts.
- Pipeline inspector for debugging sources, documents, evidence and drafts.
- Company profile match using mission, domain, technology, work model, KRITIS and exclusion weights.

Status: **Implemented / Experimental**. Foundations are present, but no production crawler, scheduler or automated research agent exists.

### Application Package

- Job cover-letter generation.
- Context resume text generation.
- Company initiative letter generation.
- Candidate insight extraction, ranking and export presentation.
- HTML application package.
- ZIP export with attachments.
- Full PDF package when a real HTML-to-PDF renderer is available.
- PDF/image attachment merge into final PDF through `pypdf`.

Status: **Partially implemented** because final PDF export depends on local renderer availability.

### Local LLM

- Local Ollama integration for application text, skill candidate evaluation and company knowledge review.
- Qwen model usage is supported through local Ollama configuration/defaults.
- CompanyHub can list local Ollama models for reviewer selection.

Status: **Implemented locally**, but dependent on installed models and Ollama availability.

## Experimental

- OpenLLMBench benchmark framework foundation.
- CareerHub local model benchmark runner.
- Company Knowledge LLM review.
- Candidate insight prioritization for initiative applications.
- Company concept canonicalization seed taxonomy.

## Planned

- Production-grade scheduling for repeated job/company refreshes.
- Improved OCR configuration and portability.
- Company knowledge approval flow.
- More complete public-safe demo dataset.
- More explainability around score weights and recommendation history.

## Concept

- Agent-based research and red-team workflows.
- Automated company monitoring with notifications.
- Long-term personal career memory.
- Broader standalone OpenLLMBench framework.
