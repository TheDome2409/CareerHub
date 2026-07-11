from io import BytesIO
import os

import pytesseract
from pdf2image import convert_from_bytes
from pypdf import PdfReader


TESSERACT_CMD = os.getenv("TESSERACT_CMD")
POPPLER_PATH = os.getenv("POPPLER_PATH") or None

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

DEBUG = False


def extract_text_with_ocr(
    file_bytes: bytes,
) -> str:
    try:
        images = convert_from_bytes(
            file_bytes,
            dpi=200,
            poppler_path=POPPLER_PATH,
        )
    except Exception as exc:
        raise RuntimeError(
            "OCR is not available. Install Poppler/Tesseract and set "
            "POPPLER_PATH and TESSERACT_CMD if they are not on PATH."
        ) from exc

    pages = []

    for image in images:
        try:
            text = pytesseract.image_to_string(
                image,
                lang="deu",
            )
        except Exception as exc:
            raise RuntimeError(
                "OCR is not available. Install Tesseract and set "
                "TESSERACT_CMD if it is not on PATH."
            ) from exc

        if text:
            pages.append(text)

    return "\n".join(pages)


def extract_text_from_pdf(
    file,
) -> str:
    file_bytes = file.read()

    reader = PdfReader(
        BytesIO(file_bytes)
    )

    pages = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages.append(text)

    extracted_text = "\n".join(
        pages
    )

    if len(
        extracted_text.strip()
    ) > 200:
        return extracted_text

    if DEBUG:
        print(
            "PDF enthält kaum Text. Starte OCR..."
        )

    return extract_text_with_ocr(
        file_bytes
    )
