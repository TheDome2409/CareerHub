# Manual Integration Checks

Files in this folder are not collected by pytest. They are local smoke checks
for optional system tools.

## OCR Smoke

`ocr_smoke.py` checks PDF OCR with local Tesseract and Poppler installations.

Required environment variables:

- `OCR_TEST_PDF`: path to a local PDF file
- `TESSERACT_CMD`: optional path to `tesseract.exe` if Tesseract is not on PATH
- `POPPLER_PATH`: optional path to Poppler binaries if Poppler is not on PATH

Example:

```powershell
set OCR_TEST_PDF=C:\path\to\sample.pdf
set TESSERACT_CMD=C:\path\to\tesseract.exe
set POPPLER_PATH=C:\path\to\poppler\bin
python tests\manual\ocr_smoke.py
```

## Ollama Provider Smoke

`ollama_provider_smoke.py` checks the legacy Ollama skill extraction provider
against a locally running Ollama server. It is intentionally not part of the
automated unit-test suite.

```powershell
python tests\manual\ollama_provider_smoke.py
```
