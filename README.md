# CareerHub

CareerHub is a local-first Python and Streamlit prototype for structured career matching, job analysis and application package generation.

The project combines deterministic rules, configurable scoring, document processing and optional local LLM support through Ollama. It is designed as a portfolio-grade prototype: useful for local experimentation, transparent about its limits, and careful with sensitive application data.

## Status

CareerHub is an actively developed local prototype.

Status terms used in this documentation:

- **Implemented**: available in code and covered by at least basic tests or UI/service integration.
- **Partially implemented**: functional pieces exist, but the feature is incomplete, heuristic or not fully integrated.
- **Experimental**: available for exploration, but not production-ready.
- **Planned**: described as a near-term roadmap item.
- **Concept**: architectural idea or long-term direction.


## License

CareerHub is licensed under the GNU Affero General Public License v3.0. See [`LICENSE`](LICENSE) for the full license text. Additional licensing notes are available in [`docs/licensing.md`](docs/licensing.md).

## Main Capabilities

### CareerHub Core

- **Implemented**: Streamlit UI with profile, job matching, CompanyHub and application package tabs.
- **Implemented**: profile CSV import/export for skills and profile preferences.
- **Implemented**: profile preferences for salary targets, work models and hard exclusions.
- **Implemented**: job loading from configured JSON, RSS, Bundesagentur and Remotive sources.
- **Implemented**: profile-aware job search queries for sources that support search terms.
- **Implemented**: job scoring with role, work model, salary, career, employer, skill, competency and role-mismatch components.
- **Implemented**: hard exclusion handling for selected industries, employment models and requirements.
- **Partially implemented**: OCR and PDF text extraction. PDF text extraction is implemented; OCR uses Tesseract and Poppler from PATH or the `TESSERACT_CMD` and `POPPLER_PATH` environment variables.
- **Implemented**: unknown skill candidate detection, canonicalization, candidate typing and review queue persistence.
- **Implemented**: persistent SQLite Skill Registry. Approved review candidates are inserted or merged into the registry and become available to matching immediately; YAML remains a seed/import source.
- **Implemented**: local LLM calls through Ollama for candidate evaluation and application text generation, where the required local model and Python package are available.

### Application Package Generation

- **Implemented**: cover-letter generation for a selected job through Ollama.
- **Implemented**: context-aware resume text generation through Ollama.
- **Implemented**: company initiative letter generation from a selected Company Match.
- **Implemented**: HTML application package generation.
- **Implemented**: ZIP export containing HTML and selected attachments.
- **Partially implemented**: final PDF package generation. The system can render HTML to PDF when WeasyPrint or wkhtmltopdf/pdfkit is available, then merge PDF/image attachments through pypdf. Without a real HTML-to-PDF renderer it does not offer a full final PDF.
- **Implemented**: attachment display-title cleanup and attachment overview rendering for application packages.

### CompanyHub

- **Implemented**: SQLite-backed company repository.
- **Implemented**: recommended company seeds and tracking of observed companies.
- **Implemented**: company sources, manual source fetching and raw document storage.
- **Implemented**: unified document processing foundation for HTML, PDF, DOCX, Markdown and text.
- **Implemented**: rule-based company evidence extraction with fallback evidence for real-world HTML pages.
- **Implemented**: company knowledge draft builder from evidence and canonical company concepts.
- **Implemented**: optional Ollama-based knowledge draft review. Reviewed drafts are saved as drafts, not automatically promoted as trusted company knowledge.
- **Implemented**: CompanyHub pipeline inspector for sources, documents, clean text lengths, evidence and knowledge drafts.
- **Implemented**: company-to-profile match foundation using mission, domain, technology, work model, KRITIS and exclusion weights.
- **Partially implemented**: older Company Match mode that aggregates already loaded jobs into company profiles and can generate initiative application context.
- **Experimental**: manual Example Technologies example profile for demos and tests.

### Benchmarking / OpenLLMBench

- **Experimental**: `careerhub/` contains a local Ollama benchmark runner with metadata, metrics, progress files, system health and archive foundations.
- **Concept / Foundation**: `openllmbench/` contains the beginning of a standalone benchmarking framework. It is not yet the active CareerHub runtime.

## What CareerHub Is Not

CareerHub does not make final career decisions.

It is not a recruiting platform, applicant tracking system, SaaS product or cloud service. It does not provide a production-ready crawler, scheduler, dashboard analytics product or legally binding qualification assessment.

LLM-generated content is treated as assistance. Human review remains required for application documents, skill decisions and company knowledge.

## Local Setup

Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the Streamlit app:

```powershell
start_gui.bat
```

or:

```powershell
set PYTHONPATH=%CD%\src
python -m streamlit run src\jobagent\ui\streamlit_app.py
```

Optional local tools:

- Ollama for local LLM calls.
- A model such as `qwen3:30b` if using the default LLM paths.
- wkhtmltopdf or WeasyPrint for automatic full PDF export.
- Tesseract and Poppler for OCR of scanned PDFs.

## Configuration

Important configuration files:

- `config/sources.yaml`: active job source configuration.
- `config/sources.example.yaml`: example source configuration.
- `config/profile.example.yaml`: public-safe profile example.
- `config/scoring.example.yaml`: job scoring example.
- `config/company_match_scoring.yaml`: company match scoring weights.
- `config/company_matching/company_matching.yaml`: CompanyHub profile-match weights.
- `config/taxonomy/*.yaml`: repository-backed taxonomy inputs.
- `config/company_taxonomy/*.yaml`: seed taxonomy for company concept canonicalization.
- `.env.example`: public-safe template for local environment variables such as optional OCR paths and source API identifiers.

Runtime skill knowledge is stored in SQLite through the Skill Registry tables. `config/skill_taxonomy.yaml` and taxonomy YAML files are treated as seeds, examples or import/export material, not as the only runtime source of known skills.

Personal profile files and runtime data should not be committed.

For Bundesagentur job search, configure `BUNDESAGENTUR_API_KEY` locally. The repository intentionally does not ship a concrete API key.

## Data And Privacy

Runtime data currently uses local JSON and SQLite files under `data/`. This can include review queue entries, snapshots, outcomes and company documents. Treat these as private by default.

Before publishing the repository, review:

- `data/`
- `logs/`
- `benchmarks/outputs/`
- generated application packages
- screenshots
- tests containing real names or application material

See [docs/security-and-privacy.md](docs/security-and-privacy.md) for details.

## Documentation

- [Architecture](docs/architecture.md)
- [Features](docs/features.md)
- [Security and Privacy](docs/security-and-privacy.md)
- [Demo](docs/demo.md)
- [Roadmap](docs/roadmap.md)
- [Portfolio Summary](docs/portfolio-summary.md)
- [Documentation Audit](docs/documentation-audit.md)
- [Publication Readiness Audit](docs/publication-readiness-audit.md)

OpenLLMBench foundation documentation:

- [OpenLLMBench Architecture Overview](docs/architecture/overview.md)
- [OpenLLMBench Benchmark Pipeline](docs/architecture/benchmark_pipeline.md)
- [OpenLLMBench Plugin Architecture](docs/architecture/plugin_architecture.md)
- [OpenLLMBench Telemetry](docs/architecture/telemetry.md)
- [OpenLLMBench Archive](docs/architecture/archive.md)
- [Benchmark Suites](docs/benchmark_suites/README.md)
- [Providers](docs/providers/README.md)
- [Create Benchmark Suite](docs/tutorials/create_benchmark_suite.md)
- [Create Provider](docs/tutorials/create_provider.md)
- [Quick Start](docs/tutorials/quick_start.md)
- [Create Evaluator](docs/tutorials/create_evaluator.md)
- [Create Judge](docs/tutorials/create_judge.md)
- [OpenLLMBench Philosophy](docs/philosophy.md)
- [OpenLLMBench Roadmap](ROADMAP.md)
- [Contributing](CONTRIBUTING.md)
- [License](LICENSE)
- [Code of Conduct](CODE_OF_CONDUCT.md)

## Tests

Run focused tests:

```powershell
python -m pytest test_scoring.py test_role_mismatch_penalty.py test_skill_profile_io.py
python -m pytest test_company_knowledge_builder.py test_company_profile_match_service.py
python -m pytest test_application_pdf_service.py test_company_application_package.py
```

Some tests are foundation or smoke tests. Passing tests are evidence of expected behavior, not proof of production readiness.
