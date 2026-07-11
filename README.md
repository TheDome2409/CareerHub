# CareerHub

CareerHub is a local-first Python and Streamlit prototype for explainable career
matching, job analysis, company intelligence foundations and application-package
generation.

It combines deterministic scoring, human-reviewed skill governance, document
processing, optional local LLM support through Ollama and synthetic demo data.
The project is published as a portfolio-grade open-source release: transparent,
test-backed and careful about privacy, while still clearly marked as a prototype.

## Project Status

CareerHub v0.1.0 is an **Initial Public Portfolio Release**.

Status terms used in this repository:

- **Implemented**: available in code and covered by tests, UI integration or
  service-level smoke tests.
- **Partially implemented**: functional pieces exist, but the feature depends on
  local tools, incomplete integration or manual review.
- **Experimental**: available for exploration, not stable product behavior.
- **Planned**: intended near-term work.
- **Concept**: architecture direction or long-term idea.

CareerHub is not a production recruiting platform, applicant tracking system,
cloud service or legal qualification engine. Human review is required for skill
decisions, LLM-generated text and application documents.

## Key Capabilities

### Implemented

- Streamlit UI for profile review, job matching, CompanyHub and application
  package workflows.
- Profile CSV import/export for skills and GUI-maintained preferences.
- Salary, work-model and hard-exclusion preferences.
- Job loading from configured JSON, RSS, Bundesagentur and Remotive sources.
- Profile-aware job queries for supported sources.
- Explainable job scoring with role, work model, salary, career, employer,
  skill, competency and role-mismatch components.
- Unknown skill detection, canonicalization, candidate typing and JSON review
  queue persistence.
- Persistent SQLite Skill Registry: human-approved candidates can create skills,
  merge aliases or surface type conflicts.
- CompanyHub foundations: tracked companies, sources, fetched documents,
  evidence extraction, canonical concepts, knowledge drafts and pipeline
  inspection.
- Company profile matching dimensions for mission, domains, technologies, work
  models, KRITIS affinity and exclusions.
- HTML and ZIP application package export.
- Synthetic public-safe profile, job and company examples.

### Partially Implemented

- OCR and scanned-PDF workflows: PDF text extraction is implemented; OCR depends
  on local Tesseract and Poppler setup.
- Final PDF application package: available only when a real HTML-to-PDF renderer
  such as wkhtmltopdf/pdfkit or WeasyPrint is installed.
- Company initiative application flow: functional prototype with strict prompts
  and human-review expectation.

### Experimental / Foundation

- Local Ollama benchmark runner under `careerhub/`.
- OpenLLMBench package skeleton for future standalone benchmark work.
- Company knowledge LLM review drafts.
- Company concept canonicalization seed taxonomy.

## Architecture Overview

```text
Profile / job / company source
        |
        v
Document loading and text extraction
        |
        v
Rule-based extraction and optional local LLM assistance
        |
        +--> Human Review Queue
        |        |
        |        v
        |   SQLite Skill Registry
        |
        v
Scoring, matching, evidence or knowledge draft building
        |
        v
Explainability in UI and optional application package export
```

Primary entry point:

```text
src/jobagent/ui/streamlit_app.py
```

Main layers:

- `src/jobagent/ui/` - Streamlit tabs and presentation logic.
- `src/jobagent/services/` - scoring, document processing, skill workflows,
  CompanyHub pipelines and exports.
- `src/jobagent/repositories/` - JSON/YAML/SQLite repository adapters.
- `src/jobagent/models/` - Pydantic and dataclass models.
- `src/jobagent/sources/` - job source adapters.
- `careerhub/` - experimental local benchmark runner.
- `openllmbench/` - standalone benchmark framework foundation.

More detail: [Architecture](docs/architecture.md).

## Screenshots / Demo

No screenshots are included yet. A privacy-safe screenshot plan is available in
[`docs/screenshots/README.md`](docs/screenshots/README.md). Screenshots should
only be added after review with synthetic data.

Demo flow: [docs/demo.md](docs/demo.md).

## Quick Start

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the Streamlit app on Windows:

```powershell
start_gui.bat
```

Or start manually from the repository root:

```powershell
set PYTHONPATH=%CD%\src
python -m streamlit run src\jobagent\ui\streamlit_app.py
```

For PowerShell:

```powershell
$env:PYTHONPATH = "src;."
python -m streamlit run src\jobagent\ui\streamlit_app.py
```

## Local LLM Setup

CareerHub can use Ollama for optional local LLM workflows:

- unknown skill candidate evaluation
- job/application text drafting
- company knowledge draft review
- local benchmark experiments

Install Ollama separately and pull a local model that you are licensed to use.
The repository does not distribute model weights. Model licenses vary by model
and tag.

If Ollama is unavailable, deterministic parts of CareerHub should still be
usable; LLM-backed actions show fallback or error messages.

## OCR And PDF Requirements

Implemented:

- PDF text extraction through `pypdf`.
- optional OCR adapter through `pytesseract` and `pdf2image`.
- PDF merge/export support through `pypdf`.

Optional local tools:

- Tesseract OCR
- Poppler
- wkhtmltopdf or WeasyPrint for full PDF application package rendering

Without a real HTML-to-PDF renderer, CareerHub does not offer a full final PDF
package and falls back to HTML/ZIP export paths.

## Synthetic Demo Data

Public-safe examples are included under:

- `examples/synthetic_profile/`
- `examples/synthetic_job_posting/`
- `examples/synthetic_company_profile/`
- `data/company_profiles/example_technologies.json`
- `data/company_profiles/xox.json`

These examples are synthetic and should not be treated as real application or
employer data.

## Configuration

Important public-safe configuration files:

- `config/sources.example.yaml`
- `config/profile.example.yaml`
- `config/scoring.example.yaml`
- `config/company_match_scoring.yaml`
- `config/company_matching/company_matching.yaml`
- `config/taxonomy/*.yaml`
- `config/company_taxonomy/*.yaml`
- `.env.example`

Runtime and private files are intentionally ignored, including review queues,
runtime databases, uploads, generated exports, logs and benchmark outputs.

For Bundesagentur job search, set `BUNDESAGENTUR_API_KEY` locally. The
repository does not ship a real API key.

## Test Instructions

Run the full suite:

```powershell
$env:PYTHONPATH = "src;."
python -m pytest
```

Focused examples:

```powershell
python -m pytest test_scoring.py test_role_mismatch_penalty.py test_skill_profile_io.py
python -m pytest test_company_knowledge_builder.py test_company_profile_match_service.py
python -m pytest test_application_pdf_service.py test_company_application_package.py
python -m pytest test_openllmbench_docs.py -q
```

The v0.1.0 public candidate was checked with:

- `324 passed, 3 skipped, 0 failed`
- documentation smoke: `3 passed`
- `compileall -q src`: successful

The skipped tests are for optional DuckDB benchmark archive support when DuckDB
is not installed.

## Privacy And Responsible AI

CareerHub is local-first by design. It does not require a cloud LLM service for
core deterministic workflows.

Important privacy rules:

- Do not commit real resumes, applications, certificates or generated letters.
- Do not commit runtime databases, review queues, uploads, logs or benchmark
  outputs.
- Treat local company documents as private unless they are public-safe.
- Review every LLM-generated application document before use.
- Verify local model licenses before use.

See:

- [Security and Privacy](docs/security-and-privacy.md)
- [Open-Source Due Diligence](docs/open-source-due-diligence.md)
- [Third-Party Notices](THIRD_PARTY_NOTICES.md)

## Documentation

- [Features](docs/features.md)
- [Architecture](docs/architecture.md)
- [Demo](docs/demo.md)
- [Roadmap](docs/roadmap.md)
- [Portfolio Summary](docs/portfolio-summary.md)
- [Related Work](docs/related-work.md)
- [Dependency License Inventory](docs/dependency-license-inventory.md)
- [Licensing](docs/licensing.md)
- [GitHub Release Profile](docs/github-release-profile.md)
- [Initial GitHub Issues](docs/github-initial-issues.md)
- [Release Notes v0.1.0](docs/releases/v0.1.0.md)
- [Screenshot Plan](docs/screenshots/README.md)

OpenLLMBench foundation:

- [OpenLLMBench Architecture Overview](docs/architecture/overview.md)
- [Benchmark Pipeline](docs/architecture/benchmark_pipeline.md)
- [Plugin Architecture](docs/architecture/plugin_architecture.md)
- [Telemetry](docs/architecture/telemetry.md)
- [Archive](docs/architecture/archive.md)
- [Benchmark Suites](docs/benchmark_suites/README.md)
- [Providers](docs/providers/README.md)
- [Create Benchmark Suite](docs/tutorials/create_benchmark_suite.md)
- [Create Provider](docs/tutorials/create_provider.md)
- [Quick Start](docs/tutorials/quick_start.md)
- [Create Evaluator](docs/tutorials/create_evaluator.md)
- [Create Judge](docs/tutorials/create_judge.md)
- [OpenLLMBench Philosophy](docs/philosophy.md)
- [OpenLLMBench Roadmap](ROADMAP.md)

## Related Work

CareerHub overlaps with resume builders, resume/job matchers, skill taxonomies,
local LLM tools and model benchmark frameworks. The differences and influences
are documented in [Related Work](docs/related-work.md).

## Product and Architecture Decisions

CareerHub is documented not only as code, but also as a product-development
case. The product notes explain why the project prioritized local processing,
human review, persistent skill knowledge and a clean public release boundary.

- [Product Vision](docs/product-vision.md)
- [Product Journey](docs/product-journey.md)
- [Product Owner Case Study](docs/product-owner-case-study.md)
- [Product Backlog](docs/product-backlog.md)
- [Architecture Decision Records](docs/adr/)

## Contributing

Contributions are welcome after public repository creation. Please read:

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [SECURITY.md](SECURITY.md)
- [SUPPORT.md](SUPPORT.md)

## License

CareerHub is licensed under the GNU Affero General Public License v3.0. See
[`LICENSE`](LICENSE) for the full text.

Third-party packages and optional local tools keep their own licenses. See
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and
[`docs/dependency-license-inventory.md`](docs/dependency-license-inventory.md).
