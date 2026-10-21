# Windows Quick Start

Status: **Implemented** bootstrap and diagnostics. Minimal setup was successfully
tested by the user on one clean, non-domain-joined Windows 11 Hyper-V VM with
Python 3.12.9. The subsequent Partial/OCR scenario also passed with German
Tesseract data and Poppler. Broken acceptance also passed: missing Python 3.12
was rejected, then installing 3.12.9 alongside the retained 3.15.1 allowed setup.
Domain/GPO acceptance remains open,
as do PDF-renderer and local-LLM validation; see the
[recorded VM procedures and results](windows-bootstrap-validation.md#broken-runtime-vm-test-2026-10-21).

Use a normal, non-administrator PowerShell in the extracted/cloned repository.
Install Python **3.12** first from [python.org](https://www.python.org/downloads/windows/).
The release baseline is Python 3.12.9; the bootstrap accepts 3.12.x, not untested minor versions.
Do not disable machine-wide script restrictions. If policy blocks the script, use the
Python commands below or follow your organization's approved script-review process.

## Quick Demo / Application Setup

Review the scripts, then explicitly install the application environment:

```powershell
.\setup_windows.ps1 -Install
.\start_gui.bat
```

This creates/reuses `.venv`, installs `requirements.txt` from PyPI, checks package
consistency, initializes the existing SQLite schema and Skill Registry seeds and
runs the self-test. No configuration files are copied or overwritten. No native
tools, model weights or cloud components are installed. Python packages are not
locked to exact versions yet; save `pip freeze` locally for a particular setup.

For a minimal demo, import `examples/synthetic_profile/skills.csv` in the profile
tab, inspect preferences and use the synthetic manual company profile from
`examples/synthetic_company_profile/example_technologies.json`. See
[Demo](demo.md). Ollama drafting, scanned-document OCR and final PDF rendering
are unavailable until their optional dependencies are configured. Live job
sources require network access and possibly an API identifier; there is no
automatic offline demo-job loader. Do not confuse the JSON profile fixture with
a supported full-profile GUI importer.

## Dependency Diagnostics

```powershell
.\setup_windows.ps1 -CheckOnly
.\setup_windows.ps1 -CheckOnly -Json
# Optional local HTTP checks; does not pull models or generate text:
.\setup_windows.ps1 -CheckOnly -CheckOllama
```

Before installation, `INSTALL_READY=true` and `CORE_READY=false` mean a supported
runtime is available but CareerHub's `.venv` is not installed yet. Host pip
conflicts remain visible but do not establish CareerHub dependency conflicts.
After installation, `CORE_READY` is based only on `.venv`; optional capabilities
may still be false. JSON schema 1.1 prints to stdout. A valid pre-install check
exits 0, as does a healthy installed core. Broken installed environments exit 1.
Reports can contain local executable paths: review before sharing.

## Full Local Setup

Follow the [Windows setup and dependency matrix](windows-setup.md). Configure
Tesseract + German language data, Poppler, a real HTML-to-PDF renderer and/or
Ollama only for the features you need. Then rerun the diagnostics. This is a
bootstrap script, **not** a one-click binary installer.

## Development / Manual Fallback

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe tools\careerhub_setup.py --initialize-data
.\.venv\Scripts\python.exe tools\careerhub_setup.py
$env:PYTHONPATH = 'src;.'
.\.venv\Scripts\python.exe -m pytest
.\start_gui.bat
```

The initialization command is an explicit write operation. Diagnostics without
that flag use a temporary database, not your application database. Keep backups
of existing runtime data before an upgrade.
