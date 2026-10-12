# Publication Readiness Audit

Date: 2026-07-11

Scope: **Historical private-repository audit**, before the clean public history
and later feature fixes. The 303-test result and local-file observations below
apply only to that snapshot. Current public release checks are documented in
the README; this report is retained as historical evidence.

## Verdict

Status: **Ready with minor changes**

The repository has been substantially cleaned for a future public GitHub release. Runtime data, benchmark outputs and generated archives identified in the previous audit have been removed from the Git index while remaining locally available. A fresh release-check virtual environment was created, dependencies were installed from `requirements.txt`, and the full automated test suite now passes.

This audit covers the current worktree and index state. It does not rewrite Git history and does not prove that older commits are free of sensitive content.

## What Changed For Publication Readiness

### Git Index Cleanup

The following categories were removed from the Git index and should remain local only:

- local CompanyHub SQLite runtime database
- recommendation snapshots and outcomes
- global skill candidate runtime JSON
- cached job JSON/RSS output
- company profile JSON files under `data/company_profiles/`
- benchmark outputs
- benchmark reports
- benchmark DuckDB archive
- local PDF test artifact

The files are still present locally where applicable, but `.gitignore` now covers the corresponding runtime/output paths.

### Synthetic Examples

Public-safe synthetic demo data was added under `examples/`:

- `examples/README.md`
- `examples/synthetic_profile/profile.json`
- `examples/synthetic_profile/skills.csv`
- `examples/synthetic_job_posting/it_project_coordinator.md`
- `examples/synthetic_company_profile/example_technologies.json`
- `examples/synthetic_company_profile/company_match_report.md`

These examples use fictional entities only:

- Person: Alex Beispiel
- Company: Example Technologies GmbH
- Role: IT Project Coordinator

They are intended to demonstrate profile analysis, job analysis, skill detection, review workflows, company matching and application-package context without using private application material.

### OCR Portability

OCR configuration was made portable:

- `src/jobagent/services/document_parser.py` now reads `TESSERACT_CMD` and `POPPLER_PATH` from the environment.
- No local Tesseract or Poppler paths are used as defaults.
- Missing OCR tools raise a clear runtime error when OCR is actually needed.

Manual OCR checks were moved out of pytest collection:

- old automatic path: `src/jobagent/test_ocr.py`
- new manual path: `tests/manual/ocr_smoke.py`

### Ollama Manual Smoke

The previous top-level Ollama provider smoke file executed a local Ollama request during pytest collection. It was replaced with a manual smoke script:

- old automatic path: `test_ollama_provider.py`
- new manual path: `tests/manual/ollama_provider_smoke.py`

This keeps normal unit tests reproducible even when Ollama is not running.

### Source API Configuration

The Bundesagentur source no longer embeds a concrete API key/client identifier in code. It now requires:

- `BUNDESAGENTUR_API_KEY`

The placeholder is documented in `.env.example`. No secret or concrete source credential is repeated in this report.

### Dependency Reproducibility

`requirements.txt` now includes the dependencies needed for a clean release test:

- `pytest`
- `ollama`
- `pdf2image`
- `pytesseract`
- `Pillow`
- existing runtime dependencies such as `pypdf`, `pdfkit`, `streamlit`, `pandas`, `requests`, `PyYAML`, `pydantic`, `rich` and `feedparser`

## Test Results

Fresh virtual environment:

- path: `.venv-release-check`
- Python: `3.12.9`

Verification:

```powershell
.\.venv-release-check\Scripts\python.exe -c "import pypdf, pdf2image, ollama, pytesseract, PIL; print('imports ok')"
```

Result:

- `imports ok`

Full test run:

```powershell
$env:PYTHONPATH='src;.'
.\.venv-release-check\Scripts\python.exe -m pytest --tb=short -q
```

Result:

- `303 passed`
- `3 skipped`
- runtime: `12.32s`

Targeted checks:

- `test_company_concept_normalizer.py`
- `test_company_knowledge_builder.py`
- `py_compile` for changed source files

Result:

- passed

## Remaining Manual Review Items

Before a public push, manually review local copies of:

- `data/**`
- `benchmarks/outputs/**`
- `benchmarks/reports/**`
- `benchmarks/archive/**`
- `logs/**`
- generated application packages
- screenshots or exported PDFs outside the repository

These are ignored or removed from the index, but they may still exist locally.

## Files Intentionally Kept Tracked

The following are suitable to keep tracked:

- source code under `src/`, `careerhub/` and `openllmbench/`
- tests and manual smoke scripts under `tests/`
- config examples and taxonomy seed YAML files
- benchmark task definitions under `benchmarks/prompts/`
- `.gitkeep` placeholders under benchmark input/output/report folders
- synthetic examples under `examples/`

## Known Non-Blocking Caveats

- OCR still depends on external system tools, even though paths are now configurable.
- Full PDF generation still depends on an available HTML-to-PDF renderer such as wkhtmltopdf/pdfkit or WeasyPrint.
- `BUNDESAGENTUR_API_KEY` must be configured locally for the Bundesagentur source.
- Git history has not been scanned or rewritten.
- Local ignored files remain on disk and must not be copied into a public release bundle.

## Recommended Next Steps

1. Inspect `git status --short` and verify that staged deletions are intended.
2. Review ignored local runtime data before packaging or publishing.
3. Run a secret scan over the final branch.
4. Commit the cleanup in a dedicated release-readiness commit when ready.
5. Optionally add CI with the same fresh-venv test command.
