import sys
from types import SimpleNamespace

import pytest

from jobagent.services import application_pdf_service


def _blank_pdf() -> bytes:
    from io import BytesIO

    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(
        width=72,
        height=72,
    )
    buffer = BytesIO()
    writer.write(
        buffer
    )

    return buffer.getvalue()


def test_prepare_html_for_pdf_removes_embedded_pdf_fallback():
    html = """
    <html>
    <body>
    <object data="data:application/pdf;base64,abc" type="application/pdf">
        <p>PDF-Anhang kann in diesem Browser nicht eingebettet angezeigt werden.</p>
    </object>
    <p>Example Technologies Anlagenübersicht</p>
    </body>
    </html>
    """

    prepared = application_pdf_service.prepare_html_for_pdf(
        html
    )

    assert "<object" not in prepared
    assert "PDF-Anhang kann in diesem Browser" not in prepared
    assert "Example Technologies Anlagenübersicht" in prepared
    assert "PDF-Anlage siehe Anlagenübersicht" in prepared


def test_render_application_pdf_uses_real_renderer_input(monkeypatch):
    captured = {}

    def fake_weasyprint(html_content):
        captured["html"] = html_content

        return "PDF: Example Technologies Anschreiben mit Umlauten aeoeue".encode("utf-8")

    monkeypatch.setattr(
        application_pdf_service,
        "_render_with_weasyprint",
        fake_weasyprint,
    )
    monkeypatch.setattr(
        application_pdf_service,
        "_render_with_pdfkit",
        lambda _html: None,
    )

    pdf = application_pdf_service.render_application_pdf(
        """
        <html>
        <head><style>body { color: red; }</style></head>
        <body>
        <h1>Example Technologies</h1>
        <p>Anschreiben aeoeue</p>
        <object><p>PDF-Anhang kann in diesem Browser nicht eingebettet angezeigt werden.</p></object>
        </body>
        </html>
        """
    )

    assert b"Example Technologies" in pdf
    assert b"aeoeue" in pdf
    assert "body { color: red; }" not in pdf.decode("utf-8")
    assert "PDF-Anhang kann in diesem Browser" not in captured["html"]
    assert "Anschreiben aeoeue" in captured["html"]


def test_render_application_pdf_logs_size_metrics(monkeypatch, tmp_path):
    log_file = tmp_path / "careerhub_pdf_export.log"

    monkeypatch.setattr(
        application_pdf_service,
        "PDF_LOG_FILE",
        log_file,
    )
    monkeypatch.setattr(
        application_pdf_service,
        "_render_with_weasyprint",
        lambda _html: b"%PDF-rendered",
    )
    monkeypatch.setattr(
        application_pdf_service,
        "_render_with_pdfkit",
        lambda _html: None,
    )

    application_pdf_service.render_application_pdf(
        (
            "<html><body>"
            "<img src=\"data:image/jpeg;base64,YWJjZA==\">"
            "Example Technologies"
            "</body></html>"
        )
    )

    log_content = log_file.read_text(
        encoding="utf-8"
    )

    assert "html_bytes=" in log_content
    assert "embedded_image_bytes=4" in log_content
    assert "pdf_bytes=13" in log_content


def test_render_application_pdf_returns_none_without_renderer(monkeypatch):
    monkeypatch.setattr(
        application_pdf_service,
        "_render_with_weasyprint",
        lambda _html: None,
    )
    monkeypatch.setattr(
        application_pdf_service,
        "_render_with_pdfkit",
        lambda _html: None,
    )

    assert application_pdf_service.render_application_pdf("<html></html>") is None


def test_find_wkhtmltopdf_detects_fixed_windows_path(monkeypatch, tmp_path):
    wkhtmltopdf = tmp_path / "wkhtmltopdf.exe"
    wkhtmltopdf.write_bytes(
        b""
    )

    monkeypatch.setattr(
        application_pdf_service.shutil,
        "which",
        lambda _command: None,
    )
    monkeypatch.setattr(
        application_pdf_service,
        "WKHTMLTOPDF_WINDOWS_PATHS",
        [
            wkhtmltopdf,
        ],
    )

    assert application_pdf_service.find_wkhtmltopdf() == str(wkhtmltopdf)


def test_pdfkit_renderer_uses_explicit_wkhtmltopdf_configuration(
    monkeypatch,
):
    captured = {}
    configuration = object()
    wkhtmltopdf_path = (
        r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    )

    def fake_configuration(wkhtmltopdf):
        captured["wkhtmltopdf"] = wkhtmltopdf

        return configuration

    def fake_from_string(
        html_content,
        output_path,
        configuration=None,
        options=None,
    ):
        captured["html"] = html_content
        captured["output_path"] = output_path
        captured["configuration"] = configuration
        captured["options"] = options

        return b"%PDF-pdfkit"

    fake_pdfkit = SimpleNamespace(
        configuration=fake_configuration,
        from_string=fake_from_string,
    )

    monkeypatch.setitem(
        sys.modules,
        "pdfkit",
        fake_pdfkit,
    )
    monkeypatch.setattr(
        application_pdf_service,
        "find_wkhtmltopdf",
        lambda: wkhtmltopdf_path,
    )

    pdf = application_pdf_service._render_with_pdfkit(
        "<html><body>Example Technologies</body></html>"
    )

    assert pdf == b"%PDF-pdfkit"
    assert captured["wkhtmltopdf"] == wkhtmltopdf_path
    assert captured["configuration"] is configuration
    assert captured["options"]["encoding"] == "UTF-8"


def test_html_pdf_renderer_status_reports_pdfkit_and_binary(monkeypatch):
    wkhtmltopdf_path = (
        r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    )

    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "weasyprint":
            raise ImportError()
        if name == "pdfkit":
            return SimpleNamespace()

        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(
        "builtins.__import__",
        fake_import,
    )
    monkeypatch.setattr(
        application_pdf_service,
        "find_wkhtmltopdf",
        lambda: wkhtmltopdf_path,
    )

    status = application_pdf_service.html_pdf_renderer_status()

    assert status["renderer_available"] is True
    assert status["renderer_name"] == "wkhtmltopdf"
    assert status["renderer_path"] == wkhtmltopdf_path
    assert status["pdfkit_import_ok"] is True


def test_html_pdf_renderer_status_reports_missing_renderer(monkeypatch):
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name in {
            "weasyprint",
            "pdfkit",
        }:
            raise ImportError()

        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(
        "builtins.__import__",
        fake_import,
    )
    monkeypatch.setattr(
        application_pdf_service,
        "find_wkhtmltopdf",
        lambda: None,
    )

    status = application_pdf_service.html_pdf_renderer_status()

    assert status["renderer_available"] is False
    assert status["renderer_name"] == ""
    assert status["renderer_path"] == ""
    assert status["pdfkit_import_ok"] is False


def test_merge_pdf_documents_preserves_document_order():
    first = _blank_pdf()
    second = _blank_pdf()

    merged = application_pdf_service.merge_pdf_documents(
        [
            first,
            second,
        ]
    )

    from io import BytesIO

    from pypdf import PdfReader

    reader = PdfReader(
        BytesIO(merged)
    )

    assert len(reader.pages) == 2


@pytest.mark.parametrize("name, content", [
    ("corrupt.pdf", b"%PDF broken"),
    ("empty.pdf", b""),
    ("broken.png", b"not an image"),
])
def test_final_pdf_fails_with_named_invalid_attachment(monkeypatch, name, content):
    monkeypatch.setattr(application_pdf_service, "render_application_pdf", lambda _: _blank_pdf())
    with pytest.raises(application_pdf_service.PdfPackageIntegrityError) as error:
        application_pdf_service.render_final_application_pdf(
            "<html>synthetic application</html>",
            [{"name": name, "bytes": content}],
        )
    assert error.value.document_name == name
    assert name in str(error.value)


def test_merge_rejects_corrupt_base_instead_of_returning_attachment_only():
    with pytest.raises(application_pdf_service.PdfPackageIntegrityError) as error:
        application_pdf_service.merge_pdf_documents(
            [b"corrupt base", _blank_pdf()], ["Basisdokument", "certificate.pdf"]
        )
    assert error.value.document_name == "Basisdokument"


def test_pdf_ui_reports_attachment_error_without_crashing(monkeypatch):
    from jobagent.ui import application_tab

    messages = []
    monkeypatch.setattr(application_tab.st, "error", messages.append)
    monkeypatch.setattr(application_pdf_service, "render_application_pdf", lambda _: _blank_pdf())
    assert application_tab._application_pdf_bytes(
        "<html></html>", [{"name": "corrupt.pdf", "bytes": b"broken"}]
    ) is None
    assert len(messages) == 1
    assert "corrupt.pdf" in messages[0]


def test_render_final_application_pdf_appends_pdf_attachments(monkeypatch):
    base_pdf = _blank_pdf()
    attachment_pdf = _blank_pdf()

    monkeypatch.setattr(
        application_pdf_service,
        "render_application_pdf",
        lambda _html: base_pdf,
    )

    final_pdf = application_pdf_service.render_final_application_pdf(
        "<html>Example Technologies</html>",
        [
            {
                "name": "Zeugnis.pdf",
                "archive_name": "Zeugnis.pdf",
                "bytes": attachment_pdf,
            }
        ],
    )

    from io import BytesIO

    from pypdf import PdfReader

    reader = PdfReader(
        BytesIO(final_pdf)
    )

    assert len(reader.pages) == 2


def test_render_final_application_pdf_returns_none_without_renderer(monkeypatch):
    monkeypatch.setattr(
        application_pdf_service,
        "render_application_pdf",
        lambda _html: None,
    )

    assert (
        application_pdf_service.render_final_application_pdf(
            "<html>Example Technologies</html>",
            [
                {
                    "name": "Zeugnis.pdf",
                    "archive_name": "Zeugnis.pdf",
                    "bytes": _blank_pdf(),
                }
            ],
        )
        is None
    )


def test_render_final_application_pdf_returns_none_when_merge_fails(monkeypatch):
    monkeypatch.setattr(
        application_pdf_service,
        "render_application_pdf",
        lambda _html: _blank_pdf(),
    )
    monkeypatch.setattr(
        application_pdf_service,
        "merge_pdf_documents",
        lambda _documents, **_kwargs: None,
    )

    assert (
        application_pdf_service.render_final_application_pdf(
            "<html>Example Technologies</html>",
            [
                {
                    "name": "Zeugnis.pdf",
                    "archive_name": "Zeugnis.pdf",
                    "bytes": _blank_pdf(),
                }
            ],
        )
        is None
    )


def test_render_final_application_pdf_rejects_unsupported_requested_attachment(
    monkeypatch,
):
    base_pdf = _blank_pdf()

    monkeypatch.setattr(
        application_pdf_service,
        "render_application_pdf",
        lambda _html: base_pdf,
    )
    monkeypatch.setattr(
        application_pdf_service,
        "merge_pdf_documents",
        lambda _documents, **_kwargs: None,
    )

    with pytest.raises(application_pdf_service.PdfPackageIntegrityError) as error:
        application_pdf_service.render_final_application_pdf(
            "<html>Example Technologies</html>",
            [
                {
                    "name": "Hinweise.txt",
                    "archive_name": "Hinweise.txt",
                    "bytes": b"Textanlage",
                }
            ],
        )
    assert error.value.document_name == "Hinweise.txt"


def test_render_final_application_pdf_converts_image_attachments(monkeypatch):
    from io import BytesIO

    from PIL import Image
    from pypdf import PdfReader

    base_pdf = _blank_pdf()
    image_buffer = BytesIO()
    Image.new(
        "RGB",
        (20, 20),
        "white",
    ).save(
        image_buffer,
        format="PNG",
    )

    monkeypatch.setattr(
        application_pdf_service,
        "render_application_pdf",
        lambda _html: base_pdf,
    )

    final_pdf = application_pdf_service.render_final_application_pdf(
        "<html>Example Technologies</html>",
        [
            {
                "name": "Zertifikat.png",
                "archive_name": "Zertifikat.png",
                "bytes": image_buffer.getvalue(),
            }
        ],
    )

    reader = PdfReader(
        BytesIO(final_pdf)
    )

    assert len(reader.pages) == 2


def test_render_application_summary_pdf_creates_short_version(monkeypatch):
    monkeypatch.setattr(
        application_pdf_service,
        "_render_with_weasyprint",
        lambda _html: None,
    )
    monkeypatch.setattr(
        application_pdf_service,
        "_render_with_pdfkit",
        lambda _html: None,
    )

    pdf = application_pdf_service.render_application_summary_pdf(
        "PDF-Kurzfassung Initiativbewerbung Example Technologies",
        [
            {
                "title": "Anschreiben",
                "body": "Mit gro?em Interesse an Example Technologies.",
            },
            {
                "title": "Top Candidate Insights",
                "body": "CareerHub - KI-gestuetzte Produktentwicklung",
            },
            {
                "title": "Hinweis zu Anlagen",
                "body": (
                    "Die PDF-Kurzfassung enthaelt keine eingebetteten "
                    "Anlagen."
                ),
            },
        ],
        html_content=(
            "<html><head><style>body { color: red; }</style></head>"
            "<body><object><p>PDF-Anhang kann in diesem Browser nicht "
            "eingebettet angezeigt werden.</p></object></body></html>"
        ),
    )

    assert pdf.startswith(b"%PDF")
    assert b"body { color: red; }" not in pdf
    assert b"PDF-Anhang kann in diesem Browser" not in pdf
