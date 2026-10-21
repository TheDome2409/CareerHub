# Windows Bootstrap V1 Validation

Date: 2026-10-15. Scope: this working-tree implementation, not a fresh Windows
VM certification. No commit or publication was performed for this work package.

The initial V1 results below are historical, **before the status-semantics
correction**. In particular, its generic pip/core conclusion must not be read as
an assessment of an installed CareerHub `.venv`. The corrected schema and
readiness rules are documented in [Windows Setup](windows-setup.md#host-versus-careerhub-environment).

Current external acceptance evidence: [clean Hyper-V VM test, 2026-10-21](#clean-hyper-v-vm-test-2026-10-21).
The subsequent [Partial/OCR VM test](#partialocr-vm-test-2026-10-21) and
[Broken Runtime VM test](#broken-runtime-vm-test-2026-10-21) also passed.

## Automated Results

- Focused bootstrap tests: **31 passed**.
- Final full regression: **364 passed, 3 skipped, 0 failed**.
- All three skips are the existing optional DuckDB archive tests: DuckDB is
  not installed in the release-check environment.
- Existing documentation smoke: **3 passed**.
- `compileall -q src tools test_windows_setup.py`: passed.
- PowerShell parser: passed; actual `-CheckOnly -PythonExe ... -Json` invocation
  produced valid JSON and correctly propagated a failing mandatory check.
- Local Markdown targets checked; no missing local targets.
- `git diff --check`: no whitespace errors (Git reports its normal LF/CRLF
  conversion notices).

Coverage includes mocked executable/version detection, absent/broken optional
tools, custom paths, unsupported Python, no-network default, refusal of remote
or credential-bearing Ollama endpoints, model-tag checks, timeout aggregation,
venv reuse/refusal and pip-failure stopping behavior. A temporary real SQLite
database verifies seed idempotence and preservation of a human-created entry
and an unrelated configuration sentinel. No existing tests were weakened.

## Real Local Probes

Python 3.12.9 and all required application/UI imports succeeded. Temporary
SQLite schema/seed migration, synthetic PDF input, real Poppler rasterization
and real wkhtmltopdf 0.12.6 rendering succeeded. The PDF check verifies readable
synthetic text, not just a PDF header. Tesseract 5.5.0 completed the synthetic
German OCR probe after explicitly setting its executable for that process only.
No private documents were used or sent anywhere. No LLM inference was run.

The default diagnosis correctly reports Tesseract as configuration-required
when it is installed but absent from the parser's PATH/environment. It does
not silently fix the user's environment. Optional Ollama HTTP/model checks
were unit-tested with mocks, not used to claim actual inference readiness.

**The real environment check is not fully green:** the existing release-check
environment's `pip check` timed out. A bounded stack diagnostic found it stalled
in pip's module-file import path; the underlying filesystem/environment cause
was not resolved by this work package. `CORE_READY=false` and exit 1 are
therefore intentional, honest results, not suppressed failures. A direct manual
pip retry was stopped after it also stalled. The installation flow was not
claimed successfully run on this host or on a clean VM. Diagnose/resolve the
local pip import stall before calling this machine installation-ready.

## Privacy and Scope

No dedicated gitleaks/detect-secrets executable was available. Systematic text
checks covered tracked and new public-relevant files (excluding ignored
venvs/runtime directories) for key/token literals, private keys, local user
paths, identities, emails, connection strings, private IPs and internal hosts.
No new credential value or runtime/binary artifact was identified. Placeholder
configuration and a synthetic URL-userinfo rejection fixture are not secrets.

An existing privacy follow-up remains: personal/company literals in
`src/jobagent/services/candidate_insight_service.py:204-205`, plus legacy company
names in test identifiers. These predate the bootstrap and were not modified
because extraction/product behavior is outside this work package. The scan is
not a formal security audit or license clearance.

Only deployment scripts, launcher behavior, tests and relevant documentation
changed. No source services, matching, scoring, database schema, environment
semantics or third-party binaries were modified/bundled. Runtime artifacts
remain ignored. No permissions or persistent PATH settings were changed.

## Remaining Acceptance Work / V2

Resolve the host pip issue, then exercise `-Install` twice on a clean supported
Windows VM with and without optional tools. Record exact package/native
versions and verify real GUI, scan OCR quality and multi-page PDF layout
separately. Future supply-chain work includes reviewed version/hash locks and
signed native installation paths only after distributor/license verification.

## Status Semantics Correction (2026-10-15)

The previous paragraph is historical advice: **do not repair unrelated global
packages as a prerequisite for CareerHub**. Host conflicts are now diagnostic,
not evidence that a future isolated application install is broken. No global
reconciliation was performed or is recommended by the bootstrapper.

Root cause: the original checker treated the executing interpreter's imports
and pip consistency as CareerHub core checks, even without a managed `.venv`.
Schema **1.1** separates `host_pip_consistency`, `careerhub_environment`,
`careerhub_python` and `careerhub_pip_consistency`, adds `INSTALL_READY`,
`NOT_INSTALLED` / `NOT_CHECKED` and bounded sanitized `diagnostic_output`.
CareerHub imports/functional checks run only under the repository's `.venv`;
an independent release-check venv is never silently treated as the application.

Real `setup_windows.ps1 -CheckOnly -Json` verification before installation:

```text
python                    AVAILABLE
host_pip_consistency      CHECK_FAILED
careerhub_environment     NOT_INSTALLED
careerhub_pip_consistency NOT_CHECKED
INSTALL_READY=true
CORE_READY=false
Exit code=0
```

The actual global conflicts were retained as package requirement messages.
No `.venv` was created. Host packages, the independent release-check environment,
PATH and registry were not repaired/modified. Check-only child interpreters use
`-B` to avoid bytecode writes. Synthetic temporary test files remain separate.

Updated validation:

- Focused setup tests: **43 passed** (host/managed environment matrix included).
- Full regression: **376 passed, 3 skipped, 0 failed**; skips remain optional DuckDB.
- PowerShell syntax and real pre-install JSON/exit-code smoke: passed.
- Python compile/import checks and `git diff --check`: passed.
- Managed healthy/broken combinations, exact interpreter delegation and
  non-mutation are covered with isolated fixtures/mocks. No actual application
  `.venv` was created merely to obtain a post-install green report.

Clean-Windows installation/upgrade and real post-install acceptance remain
follow-ups; host dependency repair is not part of them. No commit or push.

## Clean Hyper-V VM Test (2026-10-21)

Status: **Implemented**, with user-reported successful minimal installation and
post-install diagnostics on one clean VM. This supersedes the earlier pending
fresh-VM **minimal setup** check, not the remaining full-feature acceptance work.
Evidence was supplied by the tester as a console transcript and a Windows
version screenshot; this was not a new VM run performed by the documentation agent.
Raw evidence is not copied into the repository because it contains local paths
and machine/user identifiers.

### Test Environment and Prerequisite Choices

| Parameter | Recorded value |
| --- | --- |
| Hypervisor | Hyper-V |
| CPU | 4 vCPU |
| Memory | Dynamic RAM, 4-8 GB |
| Operating system | Fresh Windows installation with updates, per tester |
| Windows edition/version | Windows 11 Pro, version 26H2, OS build 26300.9711, from supplied screenshot |
| Domain membership | Not domain-joined |
| Python runtime | Explicitly installed Python 3.12.9, 64-bit |
| PowerShell context | Non-elevated for CareerHub checks/install; elevation used only for an execution-policy adjustment |
| Optional native/AI tools | Tesseract, Poppler, HTML-to-PDF renderer and Ollama not installed |

The tester installed Python Install Manager with the following command:

```powershell
winget install 9NQ7512CXL7T
```

During its interactive configuration, the tester reports enabling increased
path-length support and allowing variables to be written in the user/HOME
context. The exact variable names and resulting settings are not captured in
the transcript. These were manual prerequisite choices, not actions performed
by CareerHub's bootstrapper. Their exact scope/elevation was not independently
verified. The offered download of the current/default runtime was **not** used;
the test runtime was selected explicitly:

```powershell
py install 3.12.9
```

The tester additionally reports that all CareerHub `-CheckOnly` and `-Install`
commands were executed from a **non-elevated PowerShell session**. A separate
elevated PowerShell session was used only to adjust PowerShell execution policy
before testing. The exact `Set-ExecutionPolicy` command and scope were not
captured, so this document does not infer them. No recorded CareerHub bootstrapper
action itself required elevation during the VM acceptance scenarios.

These commands record the tested procedure, not a claim that 3.12.9 is the
current security patch release or that every Python Manager configuration has
been validated.

### Recorded Workflow and Results

The transcript starts with an invocation that could not find
`tools/careerhub_setup.py`; subsequent invocations found the script and succeeded.
A complete repository copy, including `tools/`, is therefore part of reproducing
the successful test. No script change is inferred from that initial error.

The successful workflow was:

```powershell
.\setup_windows.ps1 -CheckOnly -Json
.\setup_windows.ps1 -Install
.\setup_windows.ps1 -CheckOnly -Json
.\.venv\Scripts\python.exe -m pip check
```

Before installation, JSON schema 1.1 reported a supported host, healthy host pip,
`careerhub_environment=NOT_INSTALLED`,
`careerhub_pip_consistency=NOT_CHECKED`, `INSTALL_READY=true` and `CORE_READY=false`.
After installation, the managed Python 3.12.9 runtime, application imports,
managed pip consistency, temporary SQLite/seed check and PDF-input check all
reported `AVAILABLE`. The separate pip invocation returned
`No broken requirements found.`

```text
INSTALL_READY=true
CORE_READY=true
OCR_READY=false
PDF_EXPORT_READY=false
LOCAL_LLM_READY=false
```

The false optional capability flags are the expected degraded/minimal setup,
not an installation failure. This confirms a real managed-environment
post-install result, beyond the earlier mocked healthy-venv scenarios.
It is not a new pytest result or a claim that visual GUI/PDF workflows passed.

### Still Open

- **Planned:** additional test on domain-joined PCs, including deployment via GPO.
  Neither domain-policy compatibility nor GPO deployment is approved by this VM test.
- **Planned:** clean-VM repeated `-Install`/upgrade acceptance. Reuse of an
  existing healthy `.venv` was exercised successfully in the Partial/OCR scenario
  below, but that is not a full clean-VM upgrade/version-matrix test.
- The optional OCR self-test is now verified by the subsequent Partial/OCR
  scenario below. PDF export/local-model workflows, visual GUI/multi-page PDF
  acceptance and the broader version matrix remain unverified by this VM evidence.

## Partial/OCR VM Test (2026-10-21)

Status: **Implemented**, with user-reported successful **Partial** acceptance
for optional OCR configuration and the supplied successful diagnostic transcript.
Machine/software parameters match the preceding minimal test: Hyper-V, 4 vCPU,
4-8 GB dynamic RAM, freshly installed/updated Windows 11 Pro 26H2 build
26300.9711, not domain-joined. Python Install Manager, explicitly selected
Python 3.12.9 and the interactive path-length/user-HOME settings were the same
as recorded above. CareerHub commands were again run non-elevated; the elevated
shell use was limited to the execution-policy adjustment described above.
This is another user-performed VM test, not a new run by the documentation agent.

### Deliberately Incomplete Configuration and Remediation

The tester deliberately installed Tesseract without the required German
language data and initially left the environment variables unset. The first
test exposed the expected configuration problem: Tesseract was found at its
installed path but reported `CONFIGURATION_REQUIRED` until `TESSERACT_CMD` was
supplied.

After `TESSERACT_CMD` was set for the process, Tesseract became `AVAILABLE`.
The OCR functional check still failed because `tesseract --list-langs` exposed
only `eng` and `osd`. After the German `deu` language data was added, the OCR
functional check became `AVAILABLE`, while overall `OCR_READY` remained false
until PDF rasterization was also available.

The supported OCR settings remain `TESSERACT_CMD` and `POPPLER_PATH`/PATH as
documented in the [setup guide](windows-setup.md). Poppler was manually installed with:

```powershell
winget install -e --id oschwartz10612.Poppler
```

This records the tester's installation command, not an automatic installation
performed by CareerHub or a new redistribution/signature assurance.

### Verified Final State

The console transcript reports Tesseract **5.5.0**, `pdftoppm` and `pdfinfo`
**25.07.0**. Both the OCR and PDF rasterization functional checks are `AVAILABLE`.
Text and JSON diagnosis (schema 1.1) agree:

```text
INSTALL_READY=true
CORE_READY=true
OCR_READY=true
PDF_EXPORT_READY=false
LOCAL_LLM_READY=false
```

Host/managed pip consistency, application imports, SQLite and PDF input also
passed. A separate managed-environment `pip check` returned
`No broken requirements found.` No PDF renderer or Ollama was installed, so
their false capability flags remain expected rather than test failures.
Raw logs/user-specific installation paths are not added to the public repository.

The tester then reran `.\setup_windows.ps1 -Install` against the existing managed
environment. Pip reported the declared requirements as already satisfied, the
post-install CareerHub environment check remained green for core and OCR, and a
final direct managed-environment `pip check` again returned
`No broken requirements found.` This provides real reuse/idempotence evidence
for the Partial/OCR state, while not claiming a full upgrade/version-matrix test.

### Acceptance Tracking

| Scenario | Status | Scope |
| --- | --- | --- |
| Minimal | Passed, user-tested | Clean VM installation and managed core diagnostics |
| Partial | Passed, user-tested | OCR configuration recovery, German OCR, Poppler rasterization, and healthy `.venv` reuse on repeated install |
| Domain / GPO | **Planned** | Domain-joined machine and GPO deployment test still pending |
| Broken | Passed, user-tested | Missing supported runtime rejected; side-by-side runtime recovery; missing pydantic detected and repaired in the virtual environment |

The expected initial Tesseract problem is partial-configuration evidence;
the separate **Broken** runtime scenario is recorded below. These acceptance scenario
labels do not claim full feature coverage: real-document OCR quality, PDF
export/layout, local LLM behavior, clean-VM upgrade/version-matrix acceptance
and GUI end-to-end checks still require their own evidence. This documentation
update does not add new automated test results or change application/setup behavior.

## Broken Runtime VM Test (2026-10-21)

Status: **Implemented**, with user-reported successful **Broken** negative/recovery
acceptance. The machine/OS parameters were identical to the preceding tests:
Hyper-V, 4 vCPU, 4-8 GB dynamic RAM, fresh updated Windows 11 Pro 26H2 build
26300.9711, not domain-joined. Python **3.15.1** was deliberately installed
instead of the supported 3.12 runtime. CareerHub checks/install were run in a
non-elevated PowerShell session; elevated shell use remained limited to the
execution-policy adjustment already described. This is a tester-supplied
observation, not an independent VM run or a general Python-version compatibility claim.

Both commands were attempted while no matching 3.12 runtime was installed:

```powershell
.\setup_windows.ps1 -CheckOnly -Json
.\setup_windows.ps1 -Install
```

Each returned the supplied Python Manager error:

```text
[ERROR] No runtime installed that matches 3.12. Try running "py install 3.12".
```

This confirms rejection of the missing supported runtime rather than silently
using Python 3.15.1 for CareerHub. The failure occurred in launcher/runtime
selection, before structured Python diagnostics: **no JSON report was emitted
even with `-Json`**. The transcript does not record numeric exit codes, so none
are inferred here. This scenario does not demonstrate every broken-environment
failure mode or promise JSON output when the prerequisite interpreter is missing.

The tester then explicitly installed Python **3.12.9** through the shell.
Preflight and installation subsequently completed successfully, per the tester.
Python **3.15.1 was not uninstalled** and remained installed separately. No
automatic removal, downgrade or global package repair is implied. The recovery
report does not include another detailed JSON transcript, so no additional
optional capability flags are inferred.

### Missing Python Requirement and Repair

The tester deliberately removed **pydantic 2.14.1** from the application's
managed `.venv` with the managed interpreter. `-CheckOnly -Json` recognized the
damaged environment rather than treating the presence of `.venv` as sufficient:

```text
python_imports              MISSING
careerhub_pip_consistency   CHECK_FAILED
sqlite                      CHECK_FAILED
pdf_input                   AVAILABLE
CORE_READY                  false
```

The import diagnostic explicitly included `pydantic` and dependent CareerHub/UI
imports. The managed pip consistency diagnostic reported:

```text
ollama 0.6.3 requires pydantic, which is not installed.
```

A direct managed-environment check reproduced the same missing requirement.
Rerunning `.\setup_windows.ps1 -Install` restored the declared requirement, and
the final direct check returned:

```text
No broken requirements found.
```

This is user-tested package-level detection/recovery evidence in addition to the
runtime-selection case. The repair concerns the application virtual environment,
not global Python packages. It does not claim arbitrary dependency-conflict
repair, destructive `.venv` reconstruction, or general upgrade acceptance.

Minimal, Partial/OCR and both Broken cases are now user-tested.
**Domain/GPO remains pending.** Full-feature OCR/PDF/LLM/GUI acceptance,
clean-VM upgrade/version-matrix testing and additional broken-environment cases
remain bounded by the evidence already described. No code or installer behavior
was changed for this record.
