from dataclasses import asdict
import json
from pathlib import Path
import subprocess
from unittest.mock import Mock

import pytest

from tools import careerhub_setup as setup


def completed(stdout='', stderr='', returncode=0):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def test_python_supported_and_unsupported():
    assert setup.check_python((3, 12, 9)).status == setup.AVAILABLE
    assert setup.check_python((3, 11, 9)).status == setup.UNSUPPORTED
    assert setup.check_python((3, 13, 0)).status == setup.UNSUPPORTED


def test_present_tool_version(monkeypatch):
    monkeypatch.setattr(setup, 'find_tool', lambda *a: ('tesseract.exe', True))
    monkeypatch.setattr(setup, 'run_command', lambda *a, **kw: completed('tesseract 5.5.0'))
    result = setup.check_tool('tesseract')
    assert result.status == setup.AVAILABLE
    assert result.version == '5.5.0'


@pytest.mark.parametrize('result', [completed('broken'), completed('5.0', returncode=1)])
def test_malformed_version_result(monkeypatch, result):
    monkeypatch.setattr(setup, 'find_tool', lambda *a: ('test.exe', True))
    monkeypatch.setattr(setup, 'run_command', lambda *a, **kw: result)
    assert setup.check_tool('tesseract').status == setup.FAILED


def test_tool_timeout(monkeypatch):
    monkeypatch.setattr(setup, 'find_tool', lambda *a: ('test.exe', True))
    def timeout(*a, **kw):
        raise subprocess.TimeoutExpired('test', 20)
    monkeypatch.setattr(setup, 'run_command', timeout)
    assert setup.check_tool('tesseract').status == setup.FAILED


def test_missing_optional_and_invalid_config(monkeypatch):
    monkeypatch.setattr(setup.shutil, 'which', lambda *a, **kw: None)
    assert setup.check_tool('tesseract', {}).status == setup.OPTIONAL
    result = setup.check_tool('tesseract', {'TESSERACT_CMD': 'missing-custom.exe'})
    assert result.status == setup.CONFIGURE
    assert not result.required


def test_custom_paths_used_without_configuration_writes(tmp_path):
    exe = tmp_path / 'tesseract.exe'
    exe.touch()
    assert setup.find_tool('tesseract', {'TESSERACT_CMD': str(exe)}) == (str(exe), True)
    poppler = tmp_path / ('pdftoppm.exe' if setup.os.name == 'nt' else 'pdftoppm')
    poppler.touch()
    assert setup.find_tool('pdftoppm', {'POPPLER_PATH': str(tmp_path)}) == (str(poppler), True)


def test_status_aggregation_does_not_fail_core_for_optional_tools():
    results = [setup.DependencyResult('python', setup.AVAILABLE, True),
               setup.DependencyResult('pdf_export', setup.OPTIONAL)]
    capabilities = setup.aggregate(results)
    assert capabilities['CORE_READY']
    assert not capabilities['PDF_EXPORT_READY']
    assert not capabilities['OCR_READY']
    results.append(setup.DependencyResult('python_imports', setup.MISSING, True))
    assert not setup.aggregate(results)['CORE_READY']


def test_no_network_without_opt_in(monkeypatch):
    opener = Mock(side_effect=AssertionError('unexpected network'))
    monkeypatch.setattr(setup, 'build_opener', opener)
    assert setup.check_ollama()[0].status == setup.OPTIONAL
    assert not opener.called


@pytest.mark.parametrize('endpoint', ['https://remote.example', 'http://localhost@remote.example',
                                     'http://localhost/path', 'http://localhost?token=placeholder'])
def test_remote_and_credential_urls_not_contacted(monkeypatch, endpoint):
    opener = Mock(side_effect=AssertionError('unexpected network'))
    monkeypatch.setattr(setup, 'build_opener', opener)
    results = setup.check_ollama(True, env={'OLLAMA_HOST': endpoint, 'OLLAMA_BASE_URL': endpoint})
    assert all(result.status == setup.CONFIGURE for result in results)
    assert not opener.called


def test_ollama_models_and_separate_endpoints(monkeypatch):
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read.return_value = json.dumps({'models': [{'name': 'qwen3:30b'}, {'name': 'demo:1'}]}).encode()
    opener = Mock()
    opener.open.return_value = response
    monkeypatch.setattr(setup, 'build_opener', lambda *a: opener)
    results = setup.check_ollama(True, env={'OLLAMA_MODEL': 'demo:1', 'OLLAMA_BASE_URL': 'http://127.0.0.1:11435'})
    assert all(result.status == setup.AVAILABLE for result in results)
    assert 'http://127.0.0.1:11435/api/tags' in [call.args[0] for call in opener.open.call_args_list]
    assert all(result.status == setup.CONFIGURE for result in setup.check_ollama(True, models=['missing:1'], env={}))


def test_ollama_connection_failure(monkeypatch):
    monkeypatch.setattr(setup, 'build_opener', Mock(side_effect=OSError('offline')))
    assert all(result.status == setup.FAILED for result in setup.check_ollama(True, env={}))


def test_import_failures_and_pip_resolution(monkeypatch):
    monkeypatch.setattr(setup.importlib, 'import_module', Mock(side_effect=ImportError))
    assert setup.check_imports().status == setup.MISSING
    runner = Mock(return_value=completed())
    monkeypatch.setattr(setup, 'run_command', runner)
    assert setup.check_pip(True).status == setup.AVAILABLE
    args = runner.call_args.args[0]
    assert '--dry-run' in args and '--isolated' in args
    assert 'https://pypi.org/simple' in args


def test_probe_timeout_is_a_check_failure(monkeypatch):
    monkeypatch.setattr(setup, 'run_command', Mock(side_effect=subprocess.TimeoutExpired('probe', 45)))
    assert setup.check_probe('pdf_export').status == setup.FAILED


def test_renderer_detection_reuses_existing_service(monkeypatch):
    from jobagent.services import application_pdf_service as pdf
    monkeypatch.setattr(pdf, 'html_pdf_renderer_status', lambda: {'renderer_available': True, 'renderer_name': 'wkhtmltopdf', 'renderer_path': 'custom.exe'})
    monkeypatch.setattr(setup, 'check_probe', lambda name: setup.DependencyResult(name, setup.AVAILABLE))
    assert setup.check_renderer().path == 'custom.exe'
    monkeypatch.setattr(pdf, 'html_pdf_renderer_status', lambda: {'renderer_available': False})
    assert setup.check_renderer().status == setup.OPTIONAL


def test_data_initialization_idempotent_and_preserves_review(tmp_path):
    from jobagent.services.skill_registry_service import find_skill, save_skill
    import shutil
    for relative in ('config/skill_taxonomy.yaml', 'config/taxonomy/aliases.yaml'):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(setup.ROOT / relative, target)
    private = tmp_path / 'config' / 'profile.yaml'
    private.write_text('user configuration sentinel', encoding='utf-8')
    setup.initialize_data(tmp_path)
    db = tmp_path / 'data' / 'companyhub.db'
    save_skill('deployment_test_unique', aliases=['test private alias'], created_by='human', source='review', db_path=db)
    setup.initialize_data(tmp_path)
    assert find_skill('test private alias', db_path=db).created_by == 'human'
    assert private.read_text(encoding='utf-8') == 'user configuration sentinel'
    import sqlite3
    with sqlite3.connect(db) as connection:
        before = connection.execute('SELECT count(*) FROM skill_registry').fetchone()[0]
    setup.initialize_data(tmp_path)
    with sqlite3.connect(db) as connection:
        assert connection.execute('SELECT count(*) FROM skill_registry').fetchone()[0] == before


def test_install_refuses_existing_nonvenv(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, 'ROOT', tmp_path)
    monkeypatch.setattr(setup, 'check_python', lambda: setup.DependencyResult('python', setup.AVAILABLE, True))
    existing = tmp_path / '.venv'
    existing.mkdir()
    sentinel = existing / 'keep.txt'
    sentinel.write_text('keep')
    with pytest.raises(RuntimeError, match='not overwritten'):
        setup.install_application()
    assert sentinel.read_text() == 'keep'


def test_install_reuses_compatible_venv_and_only_runs_expected_commands(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, 'ROOT', tmp_path)
    monkeypatch.setattr(setup, 'check_python', lambda: setup.DependencyResult('python', setup.AVAILABLE, True))
    environment = tmp_path / '.venv'
    python = environment / ('Scripts/python.exe' if setup.os.name == 'nt' else 'bin/python')
    python.parent.mkdir(parents=True)
    python.touch()
    (environment / 'pyvenv.cfg').touch()
    monkeypatch.setattr(setup, 'run_command', lambda *a, **kw: completed('3.12\n'))
    create = Mock(side_effect=AssertionError('must reuse existing venv'))
    monkeypatch.setattr(setup.venv, 'EnvBuilder', create)
    runner = Mock(return_value=completed())
    monkeypatch.setattr(setup.subprocess, 'run', runner)
    assert setup.install_application() == python
    assert '--isolated' in runner.call_args_list[0].args[0]
    assert '--initialize-data' in runner.call_args_list[-1].args[0]
    assert not create.called


def test_json_output_and_optional_failure_exit_code(monkeypatch, capsys):
    report = {'schema_version': '1.1', 'results': [asdict(setup.DependencyResult('ocr', setup.OPTIONAL))],
              'capabilities': {'CORE_READY': True, 'OCR_READY': False}}
    monkeypatch.setattr(setup, 'diagnose', lambda *a: report)
    assert setup.main(['--json']) == 0
    assert json.loads(capsys.readouterr().out) == report
    report['capabilities']['CORE_READY'] = False
    assert setup.main(['--json']) == 1


def test_launcher_and_powershell_contract():
    wrapper = Path('setup_windows.ps1').read_text(encoding='utf-8')
    assert '[switch]$Install' in wrapper and '[switch]$CheckOnly' in wrapper
    assert 'Push-Location $PSScriptRoot' in wrapper and 'Pop-Location' in wrapper
    assert 'Set-ExecutionPolicy' not in wrapper and 'RunAs' not in wrapper
    launcher = Path('start_gui.bat').read_text(encoding='utf-8')
    assert '.venv\\Scripts\\python.exe' in launcher
    assert 'set PATH=' not in launcher


def test_real_synthetic_pdf_and_sqlite_probes():
    setup.probe('pdf_input')
    setup.probe('sqlite')


def test_fresh_install_creates_venv_and_failure_stops_before_database(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, 'ROOT', tmp_path)
    monkeypatch.setattr(setup, 'check_python', lambda: setup.DependencyResult('python', setup.AVAILABLE, True))
    builder = Mock()
    monkeypatch.setattr(setup.venv, 'EnvBuilder', lambda **kw: builder)
    runner = Mock(side_effect=subprocess.CalledProcessError(1, 'pip'))
    monkeypatch.setattr(setup.subprocess, 'run', runner)
    with pytest.raises(subprocess.CalledProcessError):
        setup.install_application()
    builder.create.assert_called_once_with(tmp_path / '.venv')
    assert runner.call_count == 1
    assert not (tmp_path / 'data').exists()


def test_invalid_seed_does_not_create_runtime_data(tmp_path):
    seed = tmp_path / 'config' / 'skill_taxonomy.yaml'
    seed.parent.mkdir()
    seed.write_text('[]')
    with pytest.raises(ValueError, match='invalid taxonomy seed'):
        setup.initialize_data(tmp_path)
    assert not (tmp_path / 'data').exists()


def test_synthetic_ocr_uses_german_language_and_configured_binary(monkeypatch):
    import pytesseract
    monkeypatch.setenv('TESSERACT_CMD', 'configured-test.exe')
    monkeypatch.setattr(pytesseract.pytesseract, 'tesseract_cmd', 'before')
    monkeypatch.setattr(pytesseract, 'get_languages', lambda **kw: ['deu'])
    ocr = Mock(return_value='CareerHub Test 123')
    monkeypatch.setattr(pytesseract, 'image_to_string', ocr)
    setup.probe('ocr')
    assert ocr.call_args.kwargs['lang'] == 'deu'
    assert pytesseract.pytesseract.tesseract_cmd == 'configured-test.exe'


def test_pdf_export_probe_never_accepts_invalid_bytes(monkeypatch):
    from jobagent.services import application_pdf_service as pdf
    monkeypatch.setattr(pdf, '_render_with_weasyprint', lambda html: b'not PDF')
    monkeypatch.setattr(pdf, '_render_with_pdfkit', lambda html: None)
    with pytest.raises(RuntimeError, match='No working'):
        setup.probe('pdf_export')


def test_timeout_not_reported_as_success(monkeypatch):
    monkeypatch.setattr(setup, 'run_command', Mock(side_effect=subprocess.TimeoutExpired('pip', 30)))
    result = setup.check_pip()
    assert result.status == setup.FAILED
    assert 'timed out' in result.detail


def test_new_docs_links_exist():
    for relative in ('docs/windows-quick-start.md', 'docs/windows-setup.md', 'docs/adr/0006-windows-bootstrapper.md'):
        assert Path(relative).is_file()
        assert relative in Path('README.md').read_text(encoding='utf-8')


def test_ollama_cli_not_executed_even_for_version(monkeypatch):
    monkeypatch.setattr(setup, 'find_tool', lambda *a: ('ollama.exe', False))
    runner = Mock(side_effect=AssertionError('CLI must not contact server'))
    monkeypatch.setattr(setup, 'run_command', runner)
    assert setup.check_tool('ollama').status == setup.AVAILABLE
    assert not runner.called


def _mock_diagnosis(monkeypatch, tmp_path, host_pip=setup.AVAILABLE, managed_pip=setup.AVAILABLE, installed=False, host_status=setup.AVAILABLE):
    monkeypatch.setattr(setup, 'ROOT', tmp_path)
    monkeypatch.setattr(setup, 'check_host_python', lambda python: setup.DependencyResult('python', host_status))
    monkeypatch.setattr(setup, 'check_pip', lambda *a, **kw: setup.DependencyResult(
        kw.get('name', 'pip_consistency'), host_pip, required=kw.get('required', True),
        diagnostic_output=['synthetic-tool 1 has requirement synthetic-dependency<2, but you have synthetic-dependency 3.']))
    monkeypatch.setattr(setup, 'check_tool', lambda name: setup.DependencyResult(name, setup.OPTIONAL))
    monkeypatch.setattr(setup, 'check_ollama', lambda *a: [])
    if installed:
        environment = tmp_path / '.venv'
        python = environment / ('Scripts/python.exe' if setup.os.name == 'nt' else 'bin/python')
        python.parent.mkdir(parents=True)
        python.write_bytes(b'synthetic interpreter sentinel')
        (environment / 'pyvenv.cfg').write_text('synthetic config sentinel')
    def managed(python, *args):
        return [setup.DependencyResult(name, managed_pip if name == 'careerhub_pip_consistency' else setup.AVAILABLE, True)
                for name in ('careerhub_python', 'careerhub_pip_consistency', 'python_imports', 'sqlite', 'pdf_input')]
    runner = Mock(side_effect=managed)
    monkeypatch.setattr(setup, 'managed_runtime_results', runner)
    return runner


def test_preinstall_host_conflict_does_not_block_install(monkeypatch, tmp_path):
    runner = _mock_diagnosis(monkeypatch, tmp_path, host_pip=setup.FAILED)
    report = setup.diagnose()
    states = {item['name']: item for item in report['results']}
    assert states['host_pip_consistency']['status'] == setup.FAILED
    assert states['host_pip_consistency']['diagnostic_output']
    assert not states['host_pip_consistency']['required']
    assert states['careerhub_environment']['status'] == setup.NOT_INSTALLED
    assert states['careerhub_pip_consistency']['status'] == setup.NOT_CHECKED
    assert report['capabilities']['INSTALL_READY']
    assert not report['capabilities']['CORE_READY']
    assert not runner.called
    assert not (tmp_path / '.venv').exists()


@pytest.mark.parametrize('host_pip,managed_pip,core', [
    (setup.AVAILABLE, setup.AVAILABLE, True),
    (setup.FAILED, setup.AVAILABLE, True),
    (setup.AVAILABLE, setup.FAILED, False),
])
def test_managed_environment_is_authoritative_and_not_mutated(monkeypatch, tmp_path, host_pip, managed_pip, core):
    runner = _mock_diagnosis(monkeypatch, tmp_path, host_pip, managed_pip, installed=True)
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    report = setup.diagnose()
    states = {item['name']: item['status'] for item in report['results']}
    assert states['host_pip_consistency'] == host_pip
    assert states['careerhub_pip_consistency'] == managed_pip
    assert report['capabilities']['CORE_READY'] == core
    assert report['capabilities']['INSTALL_READY']
    expected = tmp_path / '.venv' / ('Scripts/python.exe' if setup.os.name == 'nt' else 'bin/python')
    assert runner.call_args.args[0] == expected
    assert before == {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}


@pytest.mark.parametrize('status', [setup.MISSING, setup.UNSUPPORTED])
def test_no_supported_host_and_no_venv_remains_failure(monkeypatch, tmp_path, status):
    _mock_diagnosis(monkeypatch, tmp_path, host_status=status)
    report = setup.diagnose()
    assert not report['capabilities']['INSTALL_READY']
    assert not report['capabilities']['CORE_READY']


def test_host_runtime_missing_executable(monkeypatch):
    monkeypatch.setattr(setup, 'run_command', Mock(side_effect=FileNotFoundError))
    assert setup.check_host_python('missing-python').status == setup.MISSING


def test_pip_conflict_output_preserved_and_sanitized(monkeypatch):
    runner = Mock(return_value=completed(
        'synthetic-tool 1 has requirement library<2, but you have library 3.\n'
        'synthetic-tool requires https://example.invalid/token=secret, which is not installed.\n'
        'irrelevant environment dump\n', returncode=1))
    monkeypatch.setattr(setup, 'run_command', runner)
    result = setup.check_pip(python='host-python', name='host_pip_consistency', required=False)
    assert runner.call_args.args[0][0] == 'host-python'
    assert '-B' in runner.call_args.args[0]
    assert result.diagnostic_output[0].startswith('synthetic-tool 1 has requirement')
    assert '[URL redacted]' in result.diagnostic_output[1]
    assert not any('secret' in line or 'environment dump' in line for line in result.diagnostic_output)
    assert not result.required


def test_preinstall_json_schema_and_exit_code(monkeypatch, tmp_path, capsys):
    _mock_diagnosis(monkeypatch, tmp_path, host_pip=setup.FAILED)
    assert setup.main(['--json']) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['schema_version'] == '1.1'
    assert report['capabilities']['INSTALL_READY'] is True
    assert report['capabilities']['CORE_READY'] is False
    assert 'host_pip_consistency' in {item['name'] for item in report['results']}


def test_invalid_existing_venv_not_replaced(monkeypatch, tmp_path):
    _mock_diagnosis(monkeypatch, tmp_path)
    directory = tmp_path / '.venv'
    directory.mkdir()
    sentinel = directory / 'keep.txt'
    sentinel.write_text('keep')
    report = setup.diagnose()
    assert not report['capabilities']['CORE_READY']
    assert not report['capabilities']['INSTALL_READY']
    assert sentinel.read_text() == 'keep'


def test_managed_child_uses_venv_and_disables_bytecode(monkeypatch, tmp_path):
    monkeypatch.setattr(setup, 'ROOT', tmp_path)
    environment = setup.DependencyResult('careerhub_environment', setup.AVAILABLE, True)
    results = [environment] + [setup.DependencyResult(name, setup.AVAILABLE, True) for name in
                              ('careerhub_python', 'careerhub_pip_consistency', 'python_imports', 'sqlite', 'pdf_input')]
    runner = Mock(return_value=completed(json.dumps(setup.make_report(results))))
    monkeypatch.setattr(setup, 'run_command', runner)
    python = tmp_path / '.venv' / 'Scripts' / 'python.exe'
    returned = setup.managed_runtime_results(python)
    command = runner.call_args.args[0]
    assert command[0] == str(python) and '-B' in command and '--managed-check' in command
    assert 'careerhub_pip_consistency' in {item.name for item in returned}
    assert 'careerhub_environment' not in {item.name for item in returned}


def test_incomplete_managed_child_report_never_means_ready(monkeypatch, tmp_path):
    monkeypatch.setattr(setup, 'ROOT', tmp_path)
    monkeypatch.setattr(setup, 'run_command', lambda *a, **kw: completed('{"schema_version":"1.1","results":[]}'))
    with pytest.raises(ValueError, match='Incomplete'):
        setup.managed_runtime_results(tmp_path / '.venv' / 'python.exe')
