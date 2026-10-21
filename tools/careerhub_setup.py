"""Explicit environment setup and synthetic local self-tests, separate from product logic."""

import argparse
from contextlib import closing
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import importlib
import importlib.metadata
import gc
from io import BytesIO
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener
import venv


ROOT = Path(__file__).resolve().parents[1]
IMPORTS = ("pydantic", "yaml", "rich", "feedparser", "streamlit", "pandas",
           "requests", "pypdf", "pdfkit", "ollama", "pdf2image", "pytesseract", "PIL")
AVAILABLE = "AVAILABLE"
MISSING = "MISSING"
UNSUPPORTED = "VERSION_UNSUPPORTED"
CONFIGURE = "CONFIGURATION_REQUIRED"
OPTIONAL = "OPTIONAL_NOT_INSTALLED"
FAILED = "CHECK_FAILED"
NOT_INSTALLED = "NOT_INSTALLED"
NOT_CHECKED = "NOT_CHECKED"


@dataclass
class DependencyResult:
    name: str
    status: str
    required: bool = False
    path: str | None = None
    version: str | None = None
    detail: str = ""
    remediation: str = "See docs/windows-setup.md."
    diagnostic_output: list[str] = field(default_factory=list)


def run_command(args, timeout=20):
    return subprocess.run([str(arg) for arg in args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout, check=False)


def check_python(version=None):
    version = version or sys.version_info[:3]
    return DependencyResult(
        "python", AVAILABLE if tuple(version[:2]) == (3, 12) else UNSUPPORTED,
        required=True, path=sys.executable, version=".".join(map(str, version)),
        detail="3.12 is the release-tested runtime; other versions are not validated.",
        remediation="Install Python 3.12 from python.org; pass -PythonExe if needed.")


def check_imports():
    application_import_path()
    missing = []
    for module in IMPORTS + ("jobagent.ui.application_tab", "jobagent.ui.profile_tab", "jobagent.ui.jobs_tab", "jobagent.ui.company_tab"):
        try:
            importlib.import_module(module)
        except Exception:
            missing.append(module)
    return DependencyResult(
        "python_imports", MISSING if missing else AVAILABLE, required=True,
        detail="Missing/broken imports: " + ", ".join(missing) if missing else "All application adapters import.",
        remediation="Run setup_windows.ps1 -Install with Python 3.12.")


def pip_diagnostics(output):
    """Retain bounded requirement diagnostics, not arbitrary environment/traceback data."""
    lines = []
    for line in output.splitlines():
        if not any(marker in line.lower() for marker in (
            "has requirement", "which is not installed", "no broken requirements found",
        )):
            continue
        line = re.sub(r"https?://\S+", "[URL redacted]", line)
        line = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email redacted]", line)
        line = re.sub(r"(?i)[a-z]:[\\/][^\s,;]*|(?<!\w)/(?:home|Users)/[^\s,;]*", "[path redacted]", line)
        line = re.sub(r"(?i)(token|password|secret|api[_-]?key)\s*[=:]\s*[^\s,;]+", r"\1=[redacted]", line)
        lines.append(line[:300])
        if len(lines) == 12:
            break
    return lines


def check_pip(installability=False, root=ROOT, python=None, name=None, required=True):
    args = [python or sys.executable, "-B", "-m", "pip", "--isolated", "--disable-pip-version-check"]
    args += (["install", "--dry-run", "--no-input", "--index-url", "https://pypi.org/simple",
              "--ignore-installed", "-r", str(root / "requirements.txt")] if installability else ["check"])
    output = []
    try:
        result = run_command(args, timeout=180 if installability else 30)
        status = AVAILABLE if result.returncode == 0 else FAILED
        detail = "Explicit PyPI dry-run." if installability else "Installed-package consistency check."
        if result.returncode:
            detail += " pip exited with code " + str(result.returncode) + "; run pip check directly for details."
        if not installability:
            output = pip_diagnostics(result.stdout + "\n" + result.stderr)
    except subprocess.TimeoutExpired:
        status, detail = FAILED, "pip check/resolution timed out; installation state is not confirmed."
    except (OSError, subprocess.SubprocessError):
        status, detail = FAILED, "Could not execute pip."
    return DependencyResult(
        name or ("dependency_resolution" if installability else "pip_consistency"), status, required=required,
        detail=detail, diagnostic_output=output,
        remediation="Inspect python -m pip check; rerun -Install. A network failure does not prove incompatibility.")


def find_tool(name, env=None):
    env = os.environ if env is None else env
    key = "TESSERACT_CMD" if name == "tesseract" else "POPPLER_PATH"
    custom = env.get(key) if name in {"tesseract", "pdftoppm", "pdfinfo"} else None
    if custom:
        candidate = Path(custom) if name == "tesseract" else Path(custom) / (name + ".exe" if os.name == "nt" else name)
        return str(candidate) if candidate.is_file() else None, True
    found = shutil.which(name, path=env.get("PATH", os.defpath))
    if found:
        return found, False
    if name == "tesseract" and os.name == "nt":
        for variable in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            base = env.get(variable)
            if base:
                candidate = Path(base) / "Tesseract-OCR" / "tesseract.exe"
                if candidate.is_file():
                    # Existing parser uses PATH or TESSERACT_CMD, not this discovery.
                    return str(candidate), False
    return None, False


def check_tool(name, env=None):
    path, configured = find_tool(name, env)
    if not path:
        return DependencyResult(name, CONFIGURE if configured else OPTIONAL,
                                detail="Configured path missing." if configured else "Optional executable not found.")
    if name == "ollama":
        return DependencyResult(name, AVAILABLE, path=path,
                                detail="CLI discovered, not executed: even --version may contact a configured server. Use -CheckOllama for local service checks.")
    try:
        result = run_command([path, "-v" if name in {"pdftoppm", "pdfinfo"} else "--version"])
        match = re.search(r"\d+\.\d+(?:\.\d+)?", result.stdout + result.stderr)
        if result.returncode or not match:
            return DependencyResult(name, FAILED, path=path, detail="Version probe failed or returned an unrecognized version.")
        if name == "tesseract" and not configured and not shutil.which("tesseract", path=(os.environ if env is None else env).get("PATH", os.defpath)):
            return DependencyResult(name, CONFIGURE, path=path, version=match.group(),
                                    detail="Installed, but parser needs TESSERACT_CMD set to this executable.")
        return DependencyResult(name, AVAILABLE, path=path, version=match.group())
    except (OSError, subprocess.SubprocessError):
        return DependencyResult(name, FAILED, path=path, detail="Executable failed or timed out.")


def application_import_path():
    src = str(ROOT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)


def initialize_data(root=ROOT):
    """Explicit setup only. Reuse existing migrations/seeds; never replace config/DB."""
    application_import_path()
    import yaml
    for relative in ("config/skill_taxonomy.yaml", "config/taxonomy/aliases.yaml"):
        value = yaml.safe_load((root / relative).read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not value:
            raise ValueError("Missing or invalid taxonomy seed: " + relative)
    from jobagent.services.skill_registry_service import migrate_taxonomy_to_skill_registry
    for name in ("data", "logs", "uploads", "exports"):
        (root / name).mkdir(exist_ok=True)
    return migrate_taxonomy_to_skill_registry(root / "data" / "companyhub.db")


def probe(name):
    """Time-bounded child process; no user documents or application DB touched."""
    application_import_path()
    if name == "sqlite":
        from jobagent.services.skill_registry_service import migrate_taxonomy_to_skill_registry
        with tempfile.TemporaryDirectory(prefix="careerhub-check-") as directory:
            path = Path(directory) / "probe.db"
            migrate_taxonomy_to_skill_registry(path)
            # Existing service context managers commit but defer connection close.
            # Collect their unreachable connections before Windows temp cleanup.
            gc.collect()
            with closing(sqlite3.connect(path)) as connection:
                if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("SQLite integrity check failed")
                if not connection.execute("SELECT count(*) FROM skill_registry").fetchone()[0]:
                    raise RuntimeError("No seeded skills")
    elif name in {"pdf_input", "rasterization"}:
        from pypdf import PdfReader, PdfWriter
        buffer = BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.write(buffer)
        if not PdfReader(BytesIO(buffer.getvalue())).pages:
            raise RuntimeError("PDF read failed")
        if name == "rasterization":
            from pdf2image import convert_from_bytes
            if not convert_from_bytes(buffer.getvalue(), dpi=30, poppler_path=os.getenv("POPPLER_PATH") or None, timeout=10):
                raise RuntimeError("Rasterization failed")
    elif name == "ocr":
        from PIL import Image, ImageDraw, ImageFont
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD") or "tesseract"
        if "deu" not in pytesseract.get_languages(config=""):
            raise RuntimeError("German language data missing")
        image = Image.new("RGB", (600, 100), "white")
        ImageDraw.Draw(image).text((20, 20), "CareerHub Test 123", fill="black", font=ImageFont.load_default(size=32))
        if not pytesseract.image_to_string(image, lang="deu", timeout=10).strip():
            raise RuntimeError("OCR returned empty text")
    elif name == "pdf_export":
        from jobagent.services.application_pdf_service import _render_with_pdfkit, _render_with_weasyprint
        from pypdf import PdfReader
        html = '<!doctype html><meta charset="utf-8"><p>CareerHub Test</p>'
        for renderer in (_render_with_weasyprint, _render_with_pdfkit):
            try:
                result = renderer(html)
                if result:
                    pages = PdfReader(BytesIO(result)).pages
                    if any("CareerHub" in (page.extract_text() or "") for page in pages):
                        return
            except Exception:
                continue
        raise RuntimeError("No working HTML-to-PDF renderer")
    else:
        raise ValueError("Unknown probe")


def check_probe(name, required=False):
    try:
        result = run_command([sys.executable, "-B", str(Path(__file__).resolve()), "--probe", name], timeout=45)
        status = AVAILABLE if result.returncode == 0 else FAILED
    except (OSError, subprocess.SubprocessError):
        status = FAILED
    remediation = {
        "sqlite": "Check temporary-directory permissions and taxonomy seed files; do not delete application data.",
        "pdf_input": "Check/reinstall pypdf in the selected Python environment.",
        "ocr": "Verify TESSERACT_CMD/PATH and tesseract --list-langs contains deu.",
        "rasterization": "Verify POPPLER_PATH/PATH provides both pdfinfo and pdftoppm.",
        "pdf_export": "Check WeasyPrint native libraries or wkhtmltopdf/pdfkit; HTML/ZIP remain available.",
    }
    return DependencyResult(name, status, required=required,
                            detail="Synthetic functional check; no user documents used.",
                            remediation=remediation.get(name, "See docs/windows-setup.md."))


def check_renderer():
    application_import_path()
    try:
        from jobagent.services.application_pdf_service import html_pdf_renderer_status
        status = html_pdf_renderer_status()
        if not status["renderer_available"]:
            return DependencyResult("pdf_export", OPTIONAL, detail="No renderer detected; HTML/ZIP remain available.")
        result = check_probe("pdf_export")
        result.path = status.get("renderer_path") or None
        try:
            if status["renderer_name"] == "weasyprint":
                result.version = importlib.metadata.version("weasyprint")
            elif result.path:
                version = run_command([result.path, "--version"])
                match = re.search(r"\d+\.\d+(?:\.\d+)?", version.stdout + version.stderr)
                result.version = match.group() if match else None
        except Exception:
            pass  # Version metadata is best effort; the render probe is authoritative.
        result.detail += " Detected: " + status["renderer_name"]
        return result
    except Exception:
        return DependencyResult("pdf_export", FAILED, detail="Renderer detection/import failed, possibly missing native libraries.")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check_ollama(enabled=False, models=(), env=None):
    env = os.environ if env is None else env
    if not enabled:
        return [DependencyResult("ollama_service", OPTIONAL, detail="Not checked: use -CheckOllama; no request sent.")]
    endpoints = {"application": env.get("OLLAMA_HOST") or "http://localhost:11434",
                 "companyhub": env.get("OLLAMA_BASE_URL") or "http://localhost:11434"}
    selected = {"qwen3:30b", *models}
    selected.update(value for value in (env.get("COMPANYHUB_OLLAMA_MODEL"), env.get("OLLAMA_MODEL")) if value)
    results = []
    for workflow, endpoint in endpoints.items():
        if "://" not in endpoint:
            endpoint = "http://" + endpoint
        parsed = urlparse(endpoint)
        name = "ollama_" + workflow
        if (parsed.scheme not in {"http", "https"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
                or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}):
            results.append(DependencyResult(name, CONFIGURE, detail="Only local unauthenticated endpoints are checked; custom/remote URL not contacted."))
            continue
        try:
            opener = build_opener(ProxyHandler({}), NoRedirect())
            with opener.open(endpoint.rstrip("/") + "/api/tags", timeout=3) as response:
                payload = json.loads(response.read(2_000_000))
            entries = payload["models"]
            if not isinstance(entries, list) or any(not isinstance(item, dict) or not isinstance(item.get("name"), str) for item in entries):
                raise ValueError("Invalid model list")
            missing = sorted(selected - {item["name"] for item in entries})
            result = DependencyResult(name, CONFIGURE if missing else AVAILABLE,
                                      detail="Missing local tags: " + ", ".join(missing) if missing else "Service/model tags available; inference not tested.",
                                      remediation="Start Ollama; explicitly pull needed models after license/hardware review. Setup never pulls models.")
            try:
                with opener.open(endpoint.rstrip("/") + "/api/version", timeout=3) as response:
                    version = json.loads(response.read(4096)).get("version")
                    result.version = version if isinstance(version, str) else None
            except Exception:
                pass  # A version endpoint is optional, model-tag check remains valid.
            results.append(result)
        except Exception:
            results.append(DependencyResult(name, FAILED, detail="Local service unavailable/invalid response. No inference attempted."))
    return results


def aggregate(results):
    state = {result.name: result.status == AVAILABLE for result in results}
    environment = next((item.status for item in results if item.name == "careerhub_environment"), None)
    return {"INSTALL_READY": (state.get("python", False) and environment == NOT_INSTALLED)
                            or (state.get("careerhub_python", False) and environment == AVAILABLE),
            "CORE_READY": all(result.status == AVAILABLE for result in results if result.required),
            "OCR_READY": all(state.get(key, False) for key in ("tesseract", "pdftoppm", "pdfinfo", "ocr", "rasterization")),
            "PDF_EXPORT_READY": state.get("pdf_export", False),
            "LOCAL_LLM_READY": all(state.get(key, False) for key in ("ollama_application", "ollama_companyhub"))}


def diagnose_runtime(check_local_llm=False, models=(), installability=False):
    """CareerHub checks run only inside the repository-managed environment."""
    sys.dont_write_bytecode = True
    runtime = check_python()
    runtime.name = "careerhub_python"
    results = [runtime, check_imports(), check_pip(name="careerhub_pip_consistency"),
               check_probe("sqlite", True), check_probe("pdf_input", True)]
    results.extend(check_tool(name) for name in ("tesseract", "pdftoppm", "pdfinfo", "ollama"))
    by_name = {result.name: result for result in results}
    results.append(check_probe("ocr") if by_name["tesseract"].status == AVAILABLE else DependencyResult("ocr", OPTIONAL, detail="Needs configured Tesseract and deu language data."))
    results.append(check_probe("rasterization") if all(by_name[key].status == AVAILABLE for key in ("pdftoppm", "pdfinfo")) else DependencyResult("rasterization", OPTIONAL))
    results.append(check_renderer())
    results.extend(check_ollama(check_local_llm, models))
    if installability:
        results.append(check_pip(True))
    return results


def check_host_python(python):
    try:
        response = run_command([python, "-B", "-c", "import json,sys; print(json.dumps(list(sys.version_info[:3])))"])
        if response.returncode:
            raise ValueError("Runtime query failed")
        version = json.loads(response.stdout)
        if not isinstance(version, list) or len(version) != 3 or any(type(item) is not int for item in version):
            raise ValueError("Invalid version")
        result = check_python(version)
        result.required = False
        result.path = str(python)
        return result
    except FileNotFoundError:
        return DependencyResult("python", MISSING, detail="Host Python executable not found.")
    except (OSError, ValueError, subprocess.SubprocessError):
        return DependencyResult("python", FAILED, detail="Host runtime could not be checked.")


def managed_environment():
    directory = ROOT / ".venv"
    python = directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not directory.exists():
        status = CONFIGURE if directory.is_symlink() else NOT_INSTALLED
    else:
        status = AVAILABLE if (directory / "pyvenv.cfg").is_file() and python.is_file() and not directory.is_symlink() else CONFIGURE
    return DependencyResult("careerhub_environment", status, required=True, path=str(python),
                            detail="Managed CareerHub environment; not the host/global package set.",
                            remediation="Run setup_windows.ps1 -Install. Existing invalid environments are not replaced."), python


def managed_runtime_results(python, check_local_llm=False, models=(), installability=False):
    if Path(sys.prefix).resolve() == (ROOT / ".venv").resolve() and sys.prefix != sys.base_prefix:
        return diagnose_runtime(check_local_llm, models, installability)
    args = [str(python), "-B", str(Path(__file__).resolve()), "--managed-check", "--json"]
    if check_local_llm:
        args.append("--check-ollama")
    for model in models:
        args.extend(["--model", model])
    if installability:
        args.append("--check-installability")
    response = run_command(args, timeout=360)
    # Nonzero check results still carry useful diagnostics; process failure is not readiness.
    payload = json.loads(response.stdout)
    if payload.get("schema_version") != "1.1" or not isinstance(payload.get("results"), list):
        raise ValueError("Invalid managed-environment report")
    results = [DependencyResult(**item) for item in payload["results"]]
    mandatory = {"careerhub_python", "careerhub_pip_consistency", "python_imports", "sqlite", "pdf_input"}
    names = [item.name for item in results]
    if not mandatory.issubset(names) or len(names) != len(set(names)):
        raise ValueError("Incomplete managed-environment report")
    environment = next((item for item in results if item.name == "careerhub_environment"), None)
    if environment is None or environment.status != AVAILABLE:
        raise ValueError("Invalid managed environment")
    for item in results:
        if item.name in mandatory:
            item.required = True
    return [item for item in results if item.name != "careerhub_environment"]


def make_report(results):
    return {"schema_version": "1.1", "created_at": datetime.now(timezone.utc).isoformat(),
            "results": [asdict(result) for result in results], "capabilities": aggregate(results)}


def diagnose(check_local_llm=False, models=(), installability=False):
    sys.dont_write_bytecode = True
    # Even when launched from a venv, label its base interpreter's packages as host diagnostics.
    host = getattr(sys, "_base_executable", None) or sys.executable
    runtime = check_host_python(host)
    results = [runtime, check_pip(python=host, name="host_pip_consistency", required=False)]
    environment, python = managed_environment()
    results.append(environment)
    if environment.status == AVAILABLE:
        try:
            results.extend(managed_runtime_results(python, check_local_llm, models, installability))
        except (OSError, ValueError, TypeError, subprocess.SubprocessError):
            environment.status = FAILED
            results.append(DependencyResult("careerhub_pip_consistency", NOT_CHECKED,
                                            detail="Managed runtime probe failed; no host result substituted."))
    else:
        results.append(DependencyResult("careerhub_pip_consistency", NOT_CHECKED,
                                        detail="CareerHub package consistency is unknown until .venv is installed.",
                                        remediation="Run setup_windows.ps1 -Install; host conflicts do not establish CareerHub dependency conflicts."))
        results.extend(check_tool(name) for name in ("tesseract", "pdftoppm", "pdfinfo", "ollama"))
        results.extend(DependencyResult(name, NOT_CHECKED, detail="Install the managed .venv before checking application adapters.")
                       for name in ("python_imports", "sqlite", "pdf_input", "ocr", "rasterization", "pdf_export"))
        results.extend(check_ollama(check_local_llm, models))
        if installability:
            results.append(check_pip(True, required=False))
    return make_report(results)


def install_application():
    if check_python().status != AVAILABLE:
        raise RuntimeError("Setup requires Python 3.12.")
    environment = ROOT / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if environment.is_symlink():
        raise RuntimeError("Symlinked .venv not modified; use a real isolated project environment.")
    if environment.exists():
        if not (environment / "pyvenv.cfg").is_file() or not python.is_file():
            raise RuntimeError("Existing .venv is invalid; not overwritten.")
        result = run_command([python, "-c", "import sys; assert sys.prefix != sys.base_prefix; print('%d.%d' % sys.version_info[:2])"])
        if result.returncode or result.stdout.strip() != "3.12":
            raise RuntimeError("Existing .venv is not 3.12; back it up and recreate explicitly.")
    else:
        venv.EnvBuilder(with_pip=True).create(environment)
    subprocess.run([str(python), "-m", "pip", "--isolated", "--disable-pip-version-check",
                    "install", "--no-input", "--index-url", "https://pypi.org/simple",
                    "-r", str(ROOT / "requirements.txt")], check=True, timeout=900)
    subprocess.run([str(python), "-m", "pip", "--isolated", "--disable-pip-version-check", "check"], check=True, timeout=120)
    subprocess.run([str(python), str(Path(__file__).resolve()), "--initialize-data"], check=True, timeout=120)
    return python


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check-ollama", action="store_true")
    parser.add_argument("--model", action="append", default=[])
    parser.add_argument("--check-installability", action="store_true", help="Explicit PyPI dry-run network access.")
    parser.add_argument("--probe", choices=["sqlite", "pdf_input", "ocr", "rasterization", "pdf_export"], help=argparse.SUPPRESS)
    parser.add_argument("--initialize-data", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--managed-check", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.install and args.json:
        parser.error("Run --install first, then --json separately.")
    try:
        if args.probe:
            probe(args.probe)
            return 0
        if args.initialize_data:
            initialize_data()
            return 0
        if args.install:
            python = install_application()
            forwarded = [str(python), str(Path(__file__).resolve())]
            if args.check_ollama:
                forwarded.append("--check-ollama")
            for model in args.model:
                forwarded.extend(["--model", model])
            if args.check_installability:
                forwarded.append("--check-installability")
            return subprocess.run(forwarded, check=False).returncode
        if args.managed_check:
            if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve() or sys.prefix == sys.base_prefix:
                raise RuntimeError("Managed checks require this repository's isolated .venv.")
            environment, _ = managed_environment()
            report = make_report([environment] + diagnose_runtime(args.check_ollama, args.model, args.check_installability))
        else:
            report = diagnose(args.check_ollama, args.model, args.check_installability)
        if args.json:
            print(json.dumps(report, ensure_ascii=True, indent=2))
        else:
            print("CareerHub Environment Check")
            for result in report["results"]:
                print(f"{result['name']:24} {result['status']:24} {result['version'] or ''}")
                if result["path"]:
                    print("  Path: " + result["path"])
                if result["detail"]:
                    print("  " + result["detail"])
                for line in result.get("diagnostic_output", []):
                    print("  " + line)
                if result["status"] != AVAILABLE:
                    print("  Action: " + result["remediation"])
            for key, value in report["capabilities"].items():
                print(f"{key}={str(value).lower()}")
        preinstall_ready = report["capabilities"].get("INSTALL_READY", False) and any(
            item["name"] == "careerhub_environment" and item["status"] == NOT_INSTALLED
            for item in report["results"])
        return 0 if report["capabilities"]["CORE_READY"] or preinstall_ready else 1
    except Exception as exc:
        reason = str(exc) if isinstance(exc, (RuntimeError, ValueError)) else type(exc).__name__
        print("Setup/check failed: " + reason + ". See docs/windows-setup.md. Partial setup may remain; user configuration was not replaced.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
