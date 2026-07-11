# Third-Party Notices

Status: **Partially complete - dependency inventory available, legal review not performed**

CareerHub source code in this repository is licensed under the GNU Affero
General Public License v3.0. Third-party packages, optional system tools, local
services and local LLM models keep their own licenses.

The detailed dependency inventory is maintained in
[`docs/dependency-license-inventory.md`](docs/dependency-license-inventory.md).
That document records package versions, detected license metadata and review
notes from the `.venv-release-check` environment.

This file is not legal advice.

## Direct Python Dependencies

The initial public portfolio candidate directly declares these Python packages:

| Package | Detected license | CareerHub use |
| --- | --- | --- |
| `pydantic` | MIT | Data models |
| `PyYAML` | MIT | YAML configuration, taxonomy and dataset files |
| `rich` | MIT | Console output |
| `feedparser` | BSD-2-Clause | RSS source loading |
| `streamlit` | Apache-2.0 | Local UI |
| `pandas` | BSD 3-Clause License | Tables and UI dataframe rendering |
| `requests` | Apache-2.0 | HTTP calls |
| `pypdf` | BSD-3-Clause | PDF text extraction and PDF merging |
| `pdfkit` | MIT | Optional wrapper for `wkhtmltopdf` |
| `ollama` | MIT | Python client for local Ollama calls |
| `pdf2image` | MIT | Optional PDF-to-image conversion |
| `pytesseract` | Apache License 2.0 | Optional OCR adapter |
| `Pillow` | MIT-CMU | Image handling and conversion |
| `pytest` | MIT | Test runner |

## Attribution And Notices

CareerHub does not vendor the above packages. They are installed through the
Python packaging ecosystem and should be distributed with their own license
texts and notices by downstream packagers where required.

No dependency-specific full NOTICE text was identified as mandatory during this
best-effort review, but downstream redistributors should verify the exact
versions they ship.

## Optional External Tools

The following tools are not distributed with CareerHub:

- Ollama application
- local LLM model weights
- Tesseract OCR and language data
- Poppler
- wkhtmltopdf
- WeasyPrint and its native dependencies, if enabled
- DuckDB, if enabled for benchmark archiving

Users must review the license and redistribution terms of the concrete local
tools and model files they install. Local LLM model licenses vary by model,
publisher and tag. CareerHub does not grant rights to any model weights.

## Synthetic Data

The public repository includes synthetic examples under `examples/` and
selected `data/company_profiles/` files. These are intended for demos and tests
and should not be treated as real application data.
