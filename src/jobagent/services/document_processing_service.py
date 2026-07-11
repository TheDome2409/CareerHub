import re
import zipfile
from html import unescape
from io import BytesIO
from xml.etree import ElementTree

from jobagent.models.document_processing_result import DocumentProcessingResult
from jobagent.services.export_text_service import normalize_export_text


PDF_TEXT_THRESHOLD = 200
PdfReader = None
extract_text_with_ocr = None


def _pdf_reader_factory():
    global PdfReader

    if PdfReader is not None:
        return PdfReader

    try:
        from pypdf import PdfReader as Reader
    except ImportError:
        return None

    PdfReader = Reader

    return PdfReader


def _ocr_adapter():
    global extract_text_with_ocr

    if extract_text_with_ocr is not None:
        return extract_text_with_ocr

    try:
        from jobagent.services.document_parser import (
            extract_text_with_ocr as adapter,
        )
    except ImportError:
        return None

    extract_text_with_ocr = adapter

    return extract_text_with_ocr


def _bytes_content(content: bytes | str | None, encoding: str | None = None) -> bytes:
    if content is None:
        return b""

    if isinstance(content, bytes):
        return content

    return str(content).encode(
        encoding or "utf-8",
        errors="replace",
    )


def _text_content(content: bytes | str | None, encoding: str | None = None) -> str:
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    for candidate in [
        encoding,
        "utf-8-sig",
        "utf-8",
        "cp1252",
    ]:
        if not candidate:
            continue

        try:
            return content.decode(
                candidate
            )
        except UnicodeDecodeError:
            continue
        except LookupError:
            continue

    return content.decode(
        "utf-8",
        errors="replace",
    )


def _result(
    source_type: str,
    mime_type: str | None,
    encoding: str | None,
    original_size: int,
    clean_text: str,
    processing_steps: list[str],
    ocr_used: bool = False,
    language: str | None = None,
    title: str | None = None,
    metadata: dict | None = None,
) -> DocumentProcessingResult:
    normalized = normalize_export_text(
        clean_text
    )

    return DocumentProcessingResult(
        source_type=source_type,
        mime_type=mime_type,
        encoding=encoding,
        original_size=original_size,
        processed_size=len(
            normalized.encode(
                "utf-8"
            )
        ),
        ocr_used=ocr_used,
        language=language,
        title=title,
        clean_text=normalized,
        metadata=metadata or {},
        processing_steps=processing_steps,
    )


def process_html(
    content: bytes | str | None,
    mime_type: str | None = "text/html",
    encoding: str | None = None,
    title: str | None = None,
    metadata: dict | None = None,
) -> DocumentProcessingResult:
    raw_bytes = _bytes_content(
        content,
        encoding,
    )
    html = _text_content(
        content,
        encoding,
    )
    steps = [
        "loaded",
        "html_text_extraction",
    ]
    html = re.sub(
        r"<(script|style)\b[^>]*>.*?</\1>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    html = re.sub(
        r"</?(h[1-6]|p|div|section|article|main|header|footer|li|ul|ol|br)\b[^>]*>",
        "\n",
        html,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"<[^>]+>",
        " ",
        html,
    )
    text = unescape(
        text
    )
    steps.extend(
        [
            "unicode_normalization",
            "cleanup",
        ]
    )

    return _result(
        source_type="html",
        mime_type=mime_type,
        encoding=encoding,
        original_size=len(raw_bytes),
        clean_text=text,
        processing_steps=steps,
        title=title,
        metadata=metadata,
    )


def process_text(
    content: bytes | str | None,
    mime_type: str | None = "text/plain",
    encoding: str | None = None,
    title: str | None = None,
    metadata: dict | None = None,
    source_type: str = "text",
) -> DocumentProcessingResult:
    raw_bytes = _bytes_content(
        content,
        encoding,
    )
    text = _text_content(
        content,
        encoding,
    )

    return _result(
        source_type=source_type,
        mime_type=mime_type,
        encoding=encoding,
        original_size=len(raw_bytes),
        clean_text=text,
        processing_steps=[
            "loaded",
            "unicode_normalization",
            "cleanup",
        ],
        title=title,
        metadata=metadata,
    )


def process_pdf(
    content: bytes | str | None,
    mime_type: str | None = "application/pdf",
    encoding: str | None = None,
    title: str | None = None,
    metadata: dict | None = None,
) -> DocumentProcessingResult:
    file_bytes = _bytes_content(
        content,
        encoding,
    )
    steps = [
        "loaded",
        "text_extraction",
    ]
    pages = []
    reader_factory = _pdf_reader_factory()

    if file_bytes and reader_factory is not None:
        reader = reader_factory(
            BytesIO(file_bytes)
        )

        for page in reader.pages:
            text = page.extract_text()

            if text:
                pages.append(
                    text
                )

    extracted_text = "\n".join(
        pages
    )
    ocr_used = False

    if len(extracted_text.strip()) <= PDF_TEXT_THRESHOLD and file_bytes:
        ocr = _ocr_adapter()

        if ocr is not None:
            extracted_text = ocr(
                file_bytes
            )
            ocr_used = True
            steps.append(
                "ocr"
            )
        else:
            steps.append(
                "ocr_unavailable"
            )

    if reader_factory is None:
        steps.append(
            "pdf_reader_unavailable"
        )

    steps.extend(
        [
            "unicode_normalization",
            "cleanup",
        ]
    )

    return _result(
        source_type="pdf",
        mime_type=mime_type,
        encoding=encoding,
        original_size=len(file_bytes),
        clean_text=extracted_text,
        processing_steps=steps,
        ocr_used=ocr_used,
        title=title,
        metadata=metadata,
    )


def process_image(
    content: bytes | str | None,
    mime_type: str | None = None,
    encoding: str | None = None,
    title: str | None = None,
    metadata: dict | None = None,
) -> DocumentProcessingResult:
    file_bytes = _bytes_content(
        content,
        encoding,
    )

    return _result(
        source_type="image",
        mime_type=mime_type,
        encoding=encoding,
        original_size=len(file_bytes),
        clean_text="",
        processing_steps=[
            "loaded",
            "ocr_adapter_unavailable",
            "unicode_normalization",
            "cleanup",
        ],
        ocr_used=False,
        title=title,
        metadata=metadata,
    )


def process_docx(
    content: bytes | str | None,
    mime_type: str | None = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    encoding: str | None = None,
    title: str | None = None,
    metadata: dict | None = None,
) -> DocumentProcessingResult:
    file_bytes = _bytes_content(
        content,
        encoding,
    )
    paragraphs = []

    if file_bytes:
        with zipfile.ZipFile(
            BytesIO(file_bytes)
        ) as archive:
            xml = archive.read(
                "word/document.xml"
            )

        root = ElementTree.fromstring(
            xml
        )
        namespace = {
            "w": (
                "http://schemas.openxmlformats.org/"
                "wordprocessingml/2006/main"
            )
        }

        for paragraph in root.findall(
            ".//w:p",
            namespace,
        ):
            texts = [
                node.text
                for node in paragraph.findall(
                    ".//w:t",
                    namespace,
                )
                if node.text
            ]

            if texts:
                paragraphs.append(
                    "".join(texts)
                )

    return _result(
        source_type="docx",
        mime_type=mime_type,
        encoding=encoding,
        original_size=len(file_bytes),
        clean_text="\n".join(paragraphs),
        processing_steps=[
            "loaded",
            "docx_text_extraction",
            "unicode_normalization",
            "cleanup",
        ],
        title=title,
        metadata=metadata,
    )


def _detect_source_type(
    source_type: str | None,
    mime_type: str | None,
    title: str | None,
) -> str:
    if source_type:
        return source_type.lower()

    value = (mime_type or "").lower()
    name = (title or "").lower()

    if "html" in value or name.endswith((".html", ".htm")):
        return "html"

    if "pdf" in value or name.endswith(".pdf"):
        return "pdf"

    if value.startswith("image/") or name.endswith(
        (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp")
    ):
        return "image"

    if "wordprocessingml" in value or name.endswith(".docx"):
        return "docx"

    if "markdown" in value or name.endswith((".md", ".markdown")):
        return "markdown"

    return "text"


def process_document(
    content: bytes | str | None,
    source_type: str | None = None,
    mime_type: str | None = None,
    encoding: str | None = None,
    title: str | None = None,
    metadata: dict | None = None,
) -> DocumentProcessingResult:
    detected = _detect_source_type(
        source_type,
        mime_type,
        title,
    )

    if detected == "html":
        return process_html(
            content,
            mime_type=mime_type,
            encoding=encoding,
            title=title,
            metadata=metadata,
        )

    if detected == "pdf":
        return process_pdf(
            content,
            mime_type=mime_type,
            encoding=encoding,
            title=title,
            metadata=metadata,
        )

    if detected == "image":
        return process_image(
            content,
            mime_type=mime_type,
            encoding=encoding,
            title=title,
            metadata=metadata,
        )

    if detected == "docx":
        return process_docx(
            content,
            mime_type=mime_type,
            encoding=encoding,
            title=title,
            metadata=metadata,
        )

    return process_text(
        content,
        mime_type=mime_type,
        encoding=encoding,
        title=title,
        metadata=metadata,
        source_type="markdown" if detected == "markdown" else "text",
    )
