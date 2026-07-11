from jobagent.models.document_processing_result import DocumentProcessingResult
from jobagent.services import document_processing_service as service
from jobagent.services.document_processing_service import (
    process_document,
    process_html,
    process_pdf,
    process_text,
)


class FakePage:
    def __init__(self, text: str):
        self.text = text

    def extract_text(self):
        return self.text


class FakeReader:
    def __init__(self, pages):
        self.pages = pages


def test_process_html_extracts_plain_text_without_beautifulsoup():
    result = process_html(
        b"<html><head><style>.x{}</style></head><body><h1>CareerHub</h1><p>M&ouml;gliche Einsatzfelder</p><script>x()</script></body></html>",
        title="company.html",
    )

    assert isinstance(
        result,
        DocumentProcessingResult,
    )
    assert result.source_type == "html"
    assert "CareerHub" in result.clean_text
    assert "Mögliche Einsatzfelder" in result.clean_text
    assert "script" not in result.clean_text.lower()
    assert "html_text_extraction" in result.processing_steps


def test_process_text_normalizes_unicode_and_whitespace():
    result = process_text(
        "Mögliche\u00a0  Einsatzfelder\n\n\nfür CompanyHub",
        encoding="utf-8",
    )

    assert result.source_type == "text"
    assert result.clean_text == "Mögliche Einsatzfelder\n\nfür CompanyHub"
    assert result.ocr_used is False
    assert "unicode_normalization" in result.processing_steps


def test_process_pdf_with_embedded_text_does_not_use_ocr(monkeypatch):
    long_text = "CareerHub PDF Text " * 20

    monkeypatch.setattr(
        service,
        "PdfReader",
        lambda _file: FakeReader(
            [
                FakePage(
                    long_text
                )
            ]
        ),
    )
    monkeypatch.setattr(
        service,
        "extract_text_with_ocr",
        lambda _bytes: "OCR should not run",
    )

    result = process_pdf(
        b"%PDF fake"
    )

    assert result.source_type == "pdf"
    assert result.ocr_used is False
    assert "CareerHub PDF Text" in result.clean_text
    assert "ocr" not in result.processing_steps


def test_process_pdf_uses_existing_ocr_adapter_when_text_is_missing(monkeypatch):
    monkeypatch.setattr(
        service,
        "PdfReader",
        lambda _file: FakeReader(
            [
                FakePage(
                    ""
                )
            ]
        ),
    )
    monkeypatch.setattr(
        service,
        "extract_text_with_ocr",
        lambda _bytes: "OCR Ergebnis aus gescanntem PDF",
    )

    result = process_pdf(
        b"%PDF fake"
    )

    assert result.ocr_used is True
    assert result.clean_text == "OCR Ergebnis aus gescanntem PDF"
    assert "ocr" in result.processing_steps


def test_process_document_dispatches_by_mime_type_and_title():
    html_result = process_document(
        "<p>HTML</p>",
        mime_type="text/html",
    )
    markdown_result = process_document(
        "# Titel\nText",
        title="note.md",
    )

    assert html_result.source_type == "html"
    assert markdown_result.source_type == "markdown"
    assert markdown_result.clean_text == "# Titel\nText"


def test_process_empty_text_returns_empty_clean_document():
    result = process_document(
        "",
        source_type="text",
    )

    assert result.clean_text == ""
    assert result.original_size == 0
    assert result.processed_size == 0
    assert result.processing_steps == [
        "loaded",
        "unicode_normalization",
        "cleanup",
    ]
