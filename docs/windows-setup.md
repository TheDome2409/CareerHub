# Windows Setup and Diagnostics

Status: **Implemented** setup tooling, with native capability checks; not a
certified installer or a substitute for manual GUI/PDF visual acceptance.
Design and implementation plan: [ADR 0006](adr/0006-windows-bootstrapper.md).
For the short path see [Windows Quick Start](windows-quick-start.md).
Recorded results, including successful user-tested Minimal, Partial/OCR and
Broken runtime Hyper-V scenarios and the still-open Domain/GPO check:
[V1 validation](windows-bootstrap-validation.md).

## Requirements and Capability Matrix

| Dependency | Required for | Detection / functional check | Configuration |
| --- | --- | --- | --- |
| Python 3.12.x, venv, pip | Baseline | Runtime version; existing venv version; pip consistency | `-PythonExe` may select an installed interpreter |
| Python packages in `requirements.txt` | Current application imports | Imports including all four UI tab modules; `pip check` | Installed into `.venv` only |
| SQLite (Python standard library) | Registry / CompanyHub | Existing schema + seed migration and integrity check in a temporary DB | App still uses `data/companyhub.db` |
| pypdf | PDF input and merge | Synthetic PDF read/write | Installed with requirements |
| Tesseract + `deu` language data | OCR | Executable/version, language list, synthetic image OCR | `TESSERACT_CMD` executable or PATH |
| Poppler `pdfinfo` and `pdftoppm` | Scanned PDF rasterization | Executable/version and actual blank-PDF rasterization | `POPPLER_PATH` bin directory or PATH |
| WeasyPrint library + native dependencies OR wkhtmltopdf + pdfkit | Full PDF export | Existing renderer detection and actual synthetic HTML render / PDF read | Same lookup as `application_pdf_service.py` |
| Ollama service and model tags | Local AI workflows only | CLI path; optional local `/api/tags` and `/api/version` checks | Separate application and CompanyHub endpoints |

Python adapters for optional native features are currently in the common
requirements file because application modules import them. Installing those
adapters does not install their native executables. `pytest` is a declared
development dependency; its absence does not independently fail diagnostics.
No native-version compatibility matrix is claimed: native versions are reported
best effort, and functional probes determine readiness. Only the Python minor
version is explicitly gated.

## Entry Point and Installation Effects

Run `setup_windows.ps1` from any directory. It locates the repository relative
to itself. Without flags it only diagnoses. `-CheckOnly` makes that intent
explicit. `-Install` is the deliberate write/network opt-in:

1. Select explicit `-PythonExe`, otherwise `py -3.12` or compatible `python` on
   PATH, with existing `.venv` as a launcher fallback. The diagnostic orchestrator
   always inspects the repository's `.venv` separately and uses its interpreter
   for CareerHub checks. An explicit interpreter is not a substitute CareerHub
   environment. Unsupported/invalid existing venvs stop installation; none are replaced.
2. Create `.venv` only if absent. Reuse a compatible existing one; never clear it.
3. Install requirements using pip's isolated configuration and the explicit
   `https://pypi.org/simple` index, then run `pip check`.
4. Validate seed YAML presence/shape, create missing `data`, `logs`, `uploads`,
   `exports` directories and call `migrate_taxonomy_to_skill_registry()`, which
   uses the existing CompanyHub SQLite initialization/migrations.
5. Run diagnostics under the installed venv. Fail on mandatory checks only.

Repeated setup preserves configuration files and existing human-reviewed
registry provenance through the existing seed merge rules. Setup intentionally
adds schema/seed data, but does not recreate databases, replace profiles or
change YAML/environment semantics. Database migrations and pip installation
are **not one atomic transaction**. A failure stops subsequent steps; a partial
venv/migration may remain. Back up runtime data before upgrades. There is no
automatic rollback, data deletion or repair of an incompatible existing venv.
Do not run setup concurrently with another setup or a database-writing app.

No admin rights are requested. No permanent PATH/registry changes, shortcuts,
services, firewall rules or Start Menu entries are created. `start_gui.bat`
prefers `.venv`, otherwise `py -3.12`, and binds Streamlit to loopback.

## Optional Tools: Sources, Trust and Licensing

V1 auto-installs **Python requirements only**; all native tools and models are
manual choices. No third-party binaries/model weights are bundled or redistributed.
The following are documentation starting points, not automatic download URLs:

- [Python Windows downloads](https://www.python.org/downloads/windows/): use
  vendor distribution/signature verification and an appropriate supported 3.12
  patch release. 3.12.9 is the historical test baseline, not a security-update policy.
- [Tesseract installation](https://tesseract-ocr.github.io/tessdoc/Installation.html):
  upstream links Windows builds from UB Mannheim. Review that distributor and
  install German `deu` language data. Distribution may require admin rights.
- [pdf2image installation](https://pdf2image.readthedocs.io/en/latest/installation.html):
  identifies a community Windows Poppler build. This is not an upstream-signed
  Poppler binary supplied by CareerHub. Review release provenance/checksums and
  choose an approved distribution; portable extraction can avoid elevation.
- [WeasyPrint setup](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html):
  CareerHub uses the Python library, not the standalone Windows executable.
  If chosen, install the Python library into the same `.venv` and follow the
  vendor's current Windows native-library instructions. Rerun diagnostics.
- [wkhtmltopdf downloads](https://wkhtmltopdf.org/downloads.html): use only after
  reviewing its old engine/security limitations. Never feed untrusted HTML to
  this renderer; upstream warns about arbitrary-code/system compromise.
  CareerHub supports it but does not patch or secure the engine.
- [Ollama Windows setup](https://docs.ollama.com/windows): follow the vendor's
  installer documentation, not arbitrary script mirrors. Review model license
  and hardware/storage needs before an explicit `ollama pull`.

Select a concrete release intentionally and verify publisher signatures or
published hashes when available. Where upstream/distributor supplies no trusted
integrity artifact, trust is unresolved: do not claim checksum verification.
V1 does not fetch/verify native installers or automatically elevate. Manual
vendor installers may request elevation; inspect and decide separately. Pip
uses normal HTTPS validation and isolated config; requirements/transitive
dependencies are not fully pinned/hash-locked, so installation is not bitwise
reproducible or a supply-chain attestation.

Existing [third-party notices](../THIRD_PARTY_NOTICES.md) and
[license inventory](dependency-license-inventory.md) remain applicable.
Native tools/dependencies have their own terms (including copyleft components);
model licenses vary by tag. No redistribution-license clearance is asserted.

## Environment Configuration

Set variables in the launching shell **before** the app/diagnostics start:

```powershell
$env:TESSERACT_CMD = '<installed-tesseract-executable>'
$env:POPPLER_PATH = '<installed-poppler-bin-directory>'
$env:OLLAMA_HOST = 'http://localhost:11434'
$env:OLLAMA_BASE_URL = 'http://localhost:11434'
# Optional CompanyHub default; the UI also supports model selection:
$env:COMPANYHUB_OLLAMA_MODEL = '<installed-model-tag>'
.\setup_windows.ps1 -CheckOnly -CheckOllama
.\start_gui.bat
```

Do not paste angle-bracket paths literally. `TESSERACT_CMD` is a file;
`POPPLER_PATH` is a directory containing **both** Poppler tools. A Tesseract
installation discovered in a common Program Files location is reported as
`CONFIGURATION_REQUIRED` if the parser cannot find it through PATH/environment.
For wkhtmltopdf the existing PDF service checks PATH and its four conventional
Program Files locations. A custom install elsewhere must be put on PATH for
the launching process; there is no invented `WKHTMLTOPDF_PATH` setting.

`.env.example` is a reference only. No dotenv auto-loading is added. YAML
configuration, registry-first SQLite lookup and YAML seed/fallback paths are
unchanged. `BUNDESAGENTUR_API_KEY` is needed only for that live source.

Application/profile/skill LLM paths use the Ollama Python client and `OLLAMA_HOST`;
current drafting and unknown-skill workflows use `qwen3:30b`. CompanyHub's REST
reviewer uses `OLLAMA_BASE_URL` and selectable models with
`COMPANYHUB_OLLAMA_MODEL` / `OLLAMA_MODEL` defaults. Benchmark models remain in
their own config. Diagnostics check `qwen3:30b` plus selected environment model
tags and optional `-Model` arguments at both endpoints. Thus `LOCAL_LLM_READY`
is a conservative all-workflows readiness flag, not a requirement for using
just CompanyHub with a smaller model. Benchmark configs are not auto-executed
or auto-enumerated; pass extra model tags explicitly.

## Diagnostics and Exit Codes

```powershell
.\setup_windows.ps1 -CheckOnly -Json
.\setup_windows.ps1 -CheckOnly -CheckOllama -Model 'additional-local-model:tag'
# Explicit network opt-in for dependency installability, no install:
.\setup_windows.ps1 -CheckOnly -CheckInstallability
```

Direct Python equivalent: `.\.venv\Scripts\python.exe tools\careerhub_setup.py
--json` (on one line). `--check-ollama` and `--model` are the direct CLI forms.
Use `-Install` and `-Json` separately, since pip has its own textual output.

Each result includes name, required flag, path/version when obtainable,
status, detail, remediation and `diagnostic_output` (a bounded list of sanitized
pip requirement messages, empty for other checks). JSON has `schema_version: "1.1"`, UTC timestamp,
`results` and `capabilities`; stdout is the report, not a persistent log file.
Treat saved reports as local data because executable paths may be included.

| Status | Meaning |
| --- | --- |
| AVAILABLE | Relevant check succeeded (not proof of visual quality) |
| MISSING | Required Python adapters missing/broken |
| VERSION_UNSUPPORTED | Python minor version outside the release-tested baseline |
| CONFIGURATION_REQUIRED | Found but not usable/configured, missing model tag, or refused nonlocal URL |
| OPTIONAL_NOT_INSTALLED | Optional tool missing or optional service check not requested; detail distinguishes these |
| CHECK_FAILED | Execution, import, version parsing, rendering or connection failed/timed out |
| NOT_INSTALLED | The CareerHub-managed `.venv` does not exist yet |
| NOT_CHECKED | CareerHub consistency/capability not tested because its environment is absent or unusable |

Exit **0** means the installed core passed, or a supported runtime is available
and `.venv` is not installed yet (`INSTALL_READY=true`, `CORE_READY=false`).
Exit **1** means an installed core/setup check failed, an existing environment
is invalid, or no supported runtime is available. Invalid CLI arguments use exit **2**.
PowerShell may fail before invoking Python when no supported interpreter exists.
`INSTALL_READY` means a supported Python can create a new environment or the
existing managed runtime is supported; it is not proof of network access or
dependency resolution. `CORE_READY` covers the managed runtime, imports, pip
consistency, temp SQLite migration and synthetic PDF input, **only in `.venv`**.
`OCR_READY` requires native tools, German OCR and rasterization probes there.
`PDF_EXPORT_READY` requires real HTML render + parse. `LOCAL_LLM_READY` requires
local endpoint/model-tag checks, **not** inference, GPU sizing or answer quality.

### Host Versus CareerHub Environment

`python` describes the host/base runtime, and `host_pip_consistency` records its
package conflicts as informational diagnostics. The host check uses the base
interpreter even if diagnostics were launched through another virtual environment.
No packages are installed, removed or reconciled in the host environment.

Before `.venv` exists, `careerhub_environment=NOT_INSTALLED` and
`careerhub_pip_consistency=NOT_CHECKED`. CareerHub import and adapter checks are
also not checked: an unrelated host package set is not a CareerHub installation.
Run `setup_windows.ps1 -Install` to create that environment. A supported host
can yield `INSTALL_READY=true` despite host pip conflicts. `CORE_READY=false`
then means not installed, not broken or un-installable.

Once `.venv` exists, `careerhub_python`, `careerhub_pip_consistency`, imports and
functional probes use **that exact environment**, even when `-PythonExe` points
elsewhere. A healthy `.venv` is not downgraded by host conflicts; a broken `.venv`
is not rescued by a healthy host. `.venv-release-check` remains an independent
test environment, never silently substituted for the application environment.
Existing invalid environments are reported, never repaired in check-only mode.
Probe subprocesses disable bytecode writes (`-B`) and do not mutate package sets.

Requirement messages from pip are retained (up to 12 lines of 300 characters).
URLs, email addresses, common user paths and credential assignments are redacted;
unrelated output/tracebacks are not copied into the structured report. Optional
dependency-resolution dry-runs use `--ignore-installed` so global packages do
not become evidence about a future isolated install. Native-tool and LLM checks
keep their existing optional/local-only semantics.

Default checks do not fetch job/company sources or contact any LLM endpoint.
`-CheckOllama` sends only `/api/tags` and best-effort `/api/version` requests to loopback URLs, disables proxies
and redirects, and sends no profile/documents. Custom remote/authenticated URLs
are reported as configuration-required without contacting them. Product endpoint
semantics are unchanged; this restriction belongs only to diagnostics.
Functional probes run in time-bounded children on synthetic content. They do
not touch the app DB. They do not prove access to an existing locked/read-only
app DB, OCR quality on real scans, multi-page layout or UI end-to-end quality.

## Troubleshooting

- **No Python 3.12:** install it, reopen the shell or pass `-PythonExe` with the
  full executable path. No system Python is installed by this script.
- **Policy blocks PowerShell:** use the Python fallback in the quick start.
  Do not disable organization policy or machine-wide execution restrictions.
- **Pip failure:** inspect pip's visible error, connectivity and `pip check`.
  Isolated install deliberately ignores custom pip indexes; corporate mirrors
  require an organization-approved manual install, not weakened TLS validation.
  If a synchronized/cloud-placeholder folder stalls Python imports, make files
  fully local or use a local nonsynchronized checkout. A timed-out check is
  reported as failure, never as a healthy install.
- **Existing invalid venv:** preserve it and intentionally rename/remove it
  yourself before rerunning setup. There is no automatic deletion.
- **OCR false:** confirm `deu` in `tesseract --list-langs`, both Poppler tools,
  and environment paths. A CLI alone is not enough.
- **Renderer import succeeds but render fails:** verify native libraries/fonts.
  HTML/ZIP remain alternatives; no text-only PDF is labeled a final package.
- **Ollama CLI present but service/model check fails:** start the service, verify
  both endpoints/model tags, and review RAM/VRAM needs before manual download.
- **Database init fails:** stop the app, back up the DB and inspect permissions;
  don't delete user data to get a green check.

## Remove / Upgrade

Stop Streamlit first. The local `.venv` can be removed explicitly to uninstall
Python packages; vendor tools/models must be uninstalled separately through
their normal mechanisms. Preserve/back up `data`, uploads, exports, profiles
and local configuration if wanted. There is no destructive uninstall script.
Keep runtime/private files out of Git. No permissions were broadened by setup.

V2 candidates: vetted version/hash locks, a clean Windows VM acceptance matrix,
optional signed native installers after license review, and a clearer split of
Python optional extras. None are claimed implemented here.
