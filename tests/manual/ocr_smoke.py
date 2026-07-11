r"""Manual OCR smoke test.

This script is intentionally not named ``test_*.py`` so pytest does not collect
it during normal unit-test runs. It requires local Tesseract and Poppler
installations.

Usage:

    set OCR_TEST_PDF=path\to\sample.pdf
    set TESSERACT_CMD=C:\path\to\tesseract.exe
    set POPPLER_PATH=C:\path\to\poppler\bin
    python tests\manual\ocr_smoke.py
"""

from __future__ import annotations

import os
from pathlib import Path

from jobagent.services.document_parser import extract_text_from_pdf


def main() -> int:
    pdf_path = os.getenv("OCR_TEST_PDF")
    if not pdf_path:
        print("Set OCR_TEST_PDF to run the manual OCR smoke test.")
        return 0

    path = Path(pdf_path)
    if not path.exists():
        print(f"OCR_TEST_PDF does not exist: {path}")
        return 1

    with path.open("rb") as handle:
        text = extract_text_from_pdf(handle)

    print(text[:1000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
