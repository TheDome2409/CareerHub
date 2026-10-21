# ADR 0006: Explicit Windows Bootstrapper and Synthetic Self-Test

## Status

Accepted and implemented for V1, 2026-10-15. On 2026-10-21 the user supplied a
successful clean Hyper-V VM minimal-installation/post-install test and a
successful Partial/OCR configuration scenario. Broken runtime acceptance also
passed through rejection of missing Python 3.12 and side-by-side recovery.
Domain/GPO remains open, as do PDF/LLM, repeated-installation and visual acceptance.
See the [validation record](../windows-bootstrap-validation.md#broken-runtime-vm-test-2026-10-21).

## Context

Release setup used manual pip commands and a launcher selecting system Python.
OCR depends on Tesseract (`deu`) and Poppler through `document_parser.py`;
PDF export uses WeasyPrint or pdfkit/wkhtmltopdf through
`application_pdf_service.py`. Ollama has separate Python-client and CompanyHub
REST configuration. CompanyHub/Skill Registry already own SQLite migrations
and YAML seed merge behavior. Requirements and CI target Python 3.12; native
tools and model weights are not shipped. See [setup matrix](../windows-setup.md).

## Decision

Use a root PowerShell entry point and an isolated stdlib Python deployment tool,
not a packaged installer. Diagnosis is the default; `-Install` explicitly opts
into venv/pip and existing database initialization. Reuse the schema/seed
functions and renderer adapters instead of implementing another pipeline.
Keep native dependencies optional and manual. Do not modify product logic,
dotenv behavior, config files, persistent PATH or registry. No admin elevation.

Implementation plan, recorded before implementation:

1. Inspect imports, native adapters, model defaults, configuration and CI.
2. Add structured dependency results and bounded synthetic capability probes.
3. Add explicit local venv install and idempotent existing migration/seed calls.
4. Prefer that venv in the launcher; bind the local UI to loopback.
5. Add mocked detection/setup regressions, setup/security documentation and
   validate against the existing suite without weakening tests.

## Alternatives

Inno Setup/WiX/NSIS would add packaging and redistribution obligations before
the Python/native dependency matrix is locked. Vendored native binaries would
duplicate maintenance and require verified licenses/signatures. Automatic
winget/native install paths are deferred: package identifiers, sources,
elevation, release trust and user intent need explicit per-tool policy.

## Consequences

The setup is auditable and development remains ordinary Python/Streamlit. It is
not one-click, offline, atomic or fully version-locked. Users still install
native tools and suitable model weights themselves. Diagnostics use temporary
synthetic files and local opt-in tag queries, not private documents or LLM
generation. A successful check is not a visual/GUI/quality certification.
