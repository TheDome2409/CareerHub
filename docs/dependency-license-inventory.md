# Dependency License Inventory

Status: **Partially complete - requires review before commercial reuse**

This inventory was prepared for the CareerHub v0.1.0 public portfolio candidate.
It is based on:

- `requirements.txt`
- package metadata from `.venv-release-check`
- direct imports in `src/`, `careerhub/`, `openllmbench`, `app/` and tests

It is not legal advice. Python package metadata can be incomplete or ambiguous,
and optional system tools and local LLM models keep their own licenses.

## Summary

The direct Python dependencies currently installed from `requirements.txt` are
mostly permissively licensed: MIT, BSD-style or Apache-2.0. No confirmed
incompatible direct Python dependency was found during this review.

Items marked **requires review** should be checked again before a production or
commercial release, especially where metadata contains long license text,
non-SPDX wording, optional native tools or model licenses.

## Direct Python Dependencies

| Package | Installed version | Purpose in CareerHub | Detected license | License metadata source | AGPLv3 compatibility note | Notes |
| --- | ---: | --- | --- | --- | --- | --- |
| `pydantic` | 2.13.4 | Data models for profiles, jobs, company knowledge, evidence, validation and OpenLLMBench foundations | MIT | Installed package metadata: `License` | likely compatible | Permissive license metadata. |
| `PyYAML` | 6.0.3 | YAML configuration, taxonomy seed files, benchmark datasets and OpenLLMBench profiles | MIT | Installed package metadata: `License` | likely compatible | Permissive license metadata. |
| `rich` | 15.0.0 | Console output for startup and CLI-oriented helpers | MIT | Installed package metadata: `License` | likely compatible | Permissive license metadata. |
| `feedparser` | 6.0.12 | RSS job-source loading | BSD-2-Clause | Installed package metadata: `License-Expression` | likely compatible | Permissive license metadata. |
| `streamlit` | 1.59.1 | Local web UI | Apache-2.0 | Installed package metadata: `License-Expression` | likely compatible | Apache-2.0 is generally treated as GPLv3-compatible, but downstream distributors should keep notices. |
| `pandas` | 3.0.3 | Tables and UI dataframes in Streamlit views | BSD 3-Clause License | Installed package metadata: `License` | likely compatible | Metadata contains full BSD-style license text and historical copyright lines. |
| `requests` | 2.34.2 | HTTP calls for job sources, CompanyHub source fetches and Ollama REST helpers | Apache-2.0 | Installed package metadata: `License-Expression` | likely compatible | Keep dependency notices. |
| `pypdf` | 6.14.2 | PDF text extraction and PDF attachment merge | BSD-3-Clause | Installed package metadata: `License-Expression` | likely compatible | Permissive license metadata. |
| `pdfkit` | 1.0.0 | Python wrapper for optional `wkhtmltopdf` HTML-to-PDF rendering | MIT | Installed package metadata: `License` | likely compatible | `pdfkit` does not include `wkhtmltopdf`; the external binary must be installed and licensed separately. |
| `ollama` | 0.6.2 | Python client for local Ollama model calls | MIT | Installed package metadata: `License` | likely compatible | Ollama application and model weights are separate components; model licenses are user-selected. |
| `pdf2image` | 1.17.0 | Optional PDF page image conversion for OCR/preview workflows | MIT | Installed package metadata: `License` | likely compatible | Requires Poppler installed separately for normal operation. |
| `pytesseract` | 0.3.13 | Python adapter for optional Tesseract OCR | Apache License 2.0 | Installed package metadata: `License` / classifier | likely compatible | Wrapper only; Tesseract binary and language data are external. |
| `Pillow` | 12.3.0 | Image handling for attachment previews and image-to-PDF conversion | MIT-CMU | Installed package metadata: `License-Expression` | likely compatible | License expression should be retained in notices. |
| `pytest` | 9.1.1 | Test runner | MIT | Installed package metadata: `License` | likely compatible | Development/test dependency. |

## Optional Python Dependencies

| Package | Status | Purpose | License note |
| --- | --- | --- | --- |
| `weasyprint` | Not installed in the release-check environment; listed as an optional commented dependency | Alternative HTML-to-PDF renderer | Must be reviewed if enabled. It may introduce native and Python dependencies beyond this inventory. |
| `duckdb` | Not installed in the release-check environment; tests skip when absent | Optional benchmark archive backend | Must be reviewed if enabled. The current public test run skipped DuckDB-specific tests. |

## Optional System Tools And Local Services

| Component | Used for | Distributed with CareerHub? | License / review note |
| --- | --- | --- | --- |
| Ollama application | Local model serving for LLM-backed workflows | No | Ollama itself is a third-party local service. Review the installed Ollama version and its license separately. |
| Local LLM models | Skill candidate evaluation, application text generation, knowledge draft review and benchmark runs | No | Model licenses vary by model and tag. Users must verify the license of every local model they pull or use. |
| Tesseract OCR | OCR fallback for scanned PDFs/images | No | External binary and language data. Verify local installation license and language-data terms. |
| Poppler | PDF-to-image conversion used by OCR/preview workflows | No | External binary. Verify local installation license and redistribution obligations. |
| wkhtmltopdf | Optional HTML-to-PDF renderer through `pdfkit` | No | External binary. Verify local installation license and native dependencies. |
| WeasyPrint | Optional HTML-to-PDF renderer | No | Optional Python/native stack. Review before adding to required dependencies. |

## Transitive Dependencies Observed In `.venv-release-check`

The following packages were installed transitively or as tooling dependencies in
the release-check environment. They are not all imported directly by CareerHub.
This list is included to make the environment reproducible and to flag items for
future automated license inventory.

```text
altair==6.2.2
annotated-types==0.7.0
anyio==4.14.1
attrs==26.1.0
blinker==1.9.0
cachetools==7.1.4
certifi==2026.6.17
charset-normalizer==3.4.9
click==8.4.2
colorama==0.4.6
gitdb==4.0.12
GitPython==3.1.50
h11==0.16.0
httpcore==1.0.9
httptools==0.8.0
httpx==0.28.1
idna==3.18
iniconfig==2.3.0
itsdangerous==2.2.0
Jinja2==3.1.6
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
markdown-it-py==4.2.0
MarkupSafe==3.0.3
mdurl==0.1.2
narwhals==2.23.0
numpy==2.5.1
packaging==26.2
pluggy==1.6.0
protobuf==7.35.1
pyarrow==25.0.0
pydantic_core==2.46.4
pydeck==0.9.3
Pygments==2.20.0
python-dateutil==2.9.0.post0
python-multipart==0.0.32
referencing==0.37.0
rpds-py==2026.6.3
setuptools==83.0.0
sgmllib3k==1.0.0
six==1.17.0
smmap==5.0.3
starlette==1.3.1
tenacity==9.1.4
toml==0.10.2
typing-inspection==0.4.2
typing_extensions==4.16.0
tzdata==2026.3
urllib3==2.7.0
uvicorn==0.51.0
watchdog==6.0.0
websockets==16.1
wheel==0.47.0
```

## Review Notes

- Direct Python dependency metadata did not show a confirmed incompatible license.
- Optional renderer/OCR/model components are intentionally not distributed in
  this repository and need separate user-side review.
- This inventory should be regenerated when versions change or when optional
  extras such as DuckDB or WeasyPrint become required dependencies.
