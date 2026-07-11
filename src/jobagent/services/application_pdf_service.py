import base64
import re
import shutil
import site
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PDF_LOG_FILE = PROJECT_ROOT / "logs" / "careerhub_pdf_export.log"
WKHTMLTOPDF_WINDOWS_PATHS = [
    Path(r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"),
    Path(r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe"),
    Path(r"C:\Program Files\wkhtmltox\bin\wkhtmltopdf.exe"),
    Path(r"C:\Program Files (x86)\wkhtmltox\bin\wkhtmltopdf.exe"),
]


OBJECT_FALLBACK_PATTERN = re.compile(
    r"<object\b[^>]*>.*?</object>",
    flags=re.IGNORECASE | re.DOTALL,
)
IMAGE_DATA_URI_PATTERN = re.compile(
    r"data:image/(?:jpeg|jpg|png|webp);base64,([A-Za-z0-9+/=]+)",
    flags=re.IGNORECASE,
)


def _embedded_image_bytes(html_content: str) -> int:
    total = 0

    for match in IMAGE_DATA_URI_PATTERN.finditer(
        html_content or ""
    ):
        try:
            total += len(
                base64.b64decode(
                    match.group(1),
                    validate=False,
                )
            )
        except Exception:
            continue

    return total


def _log_pdf_sizes(
    html_content: str,
    pdf_bytes: bytes | None,
) -> None:
    PDF_LOG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    line = (
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        f"html_bytes={len((html_content or '').encode('utf-8'))}, "
        f"embedded_image_bytes={_embedded_image_bytes(html_content)}, "
        f"pdf_bytes={len(pdf_bytes or b'')}"
    )

    with open(
        PDF_LOG_FILE,
        "a",
        encoding="utf-8",
    ) as file:
        file.write(line + "\n")


def prepare_html_for_pdf(html_content: str) -> str:
    html_content = html_content or ""

    return OBJECT_FALLBACK_PATTERN.sub(
        (
            "<p class=\"pdf-attachment-note\">"
            "PDF-Anlage siehe Anlagenübersicht und ZIP-Datei."
            "</p>"
        ),
        html_content,
    )


def _render_with_weasyprint(html_content: str) -> bytes | None:
    try:
        from weasyprint import HTML
    except ImportError:
        return None

    try:
        return HTML(
            string=html_content,
            base_url=".",
        ).write_pdf()
    except Exception:
        return None


def _import_pdfkit():
    try:
        import pdfkit

        return pdfkit
    except ImportError:
        user_site = site.getusersitepackages()

        if user_site and user_site not in sys.path:
            sys.path.insert(
                0,
                user_site,
            )

        try:
            import pdfkit

            return pdfkit
        except ImportError:
            return None


def _render_with_pdfkit(html_content: str) -> bytes | None:
    pdfkit = _import_pdfkit()

    if pdfkit is None:
        return None

    wkhtmltopdf_path = find_wkhtmltopdf()
    configuration = None

    if wkhtmltopdf_path:
        try:
            configuration = pdfkit.configuration(
                wkhtmltopdf=wkhtmltopdf_path,
            )
        except Exception:
            configuration = None

    try:
        return pdfkit.from_string(
            html_content,
            False,
            configuration=configuration,
            options={
                "encoding": "UTF-8",
                "quiet": "",
            },
        )
    except Exception:
        return None


def find_wkhtmltopdf() -> str | None:
    command_path = shutil.which(
        "wkhtmltopdf"
    )

    if command_path:
        return command_path

    for path in WKHTMLTOPDF_WINDOWS_PATHS:
        if path.exists():
            return str(path)

    return None


def html_pdf_renderer_status() -> dict:
    status = {
        "renderer_available": False,
        "renderer_name": "",
        "renderer_path": "",
        "pdfkit_import_ok": False,
    }

    try:
        from weasyprint import HTML  # noqa: F401

        status.update(
            {
                "renderer_available": True,
                "renderer_name": "weasyprint",
            }
        )

        return status
    except ImportError:
        pass

    pdfkit = _import_pdfkit()

    if pdfkit is None:
        return status

    status["pdfkit_import_ok"] = True

    wkhtmltopdf_path = find_wkhtmltopdf()

    if wkhtmltopdf_path:
        status.update(
            {
                "renderer_available": True,
                "renderer_name": "wkhtmltopdf",
                "renderer_path": wkhtmltopdf_path,
            }
        )

    return status


def is_html_pdf_renderer_available() -> bool:
    return bool(
        html_pdf_renderer_status().get("renderer_available")
    )


def _load_font(size: int, bold: bool = False):
    try:
        from PIL import ImageFont
    except ImportError:
        return None

    font_name = "arialbd.ttf" if bold else "arial.ttf"
    font_path = Path(r"C:\Windows\Fonts") / font_name

    try:
        return ImageFont.truetype(
            str(font_path),
            size=size,
        )
    except Exception:
        return ImageFont.load_default()


def _wrap_text(draw, text: str, font, max_width: int) -> list[str]:
    lines = []

    for paragraph in (text or "").splitlines():
        paragraph = paragraph.strip()

        if not paragraph:
            lines.append("")
            continue

        words = paragraph.split()
        current = ""

        for word in words:
            candidate = f"{current} {word}".strip()
            width = draw.textlength(
                candidate,
                font=font,
            )

            if width <= max_width:
                current = candidate
                continue

            if current:
                lines.append(
                    current
                )

            current = word

        if current:
            lines.append(
                current
            )

    return lines


def _draw_wrapped_text(
    draw,
    text: str,
    font,
    x: int,
    y: int,
    max_width: int,
    line_height: int,
    fill: str = "#111827",
) -> int:
    for line in _wrap_text(
        draw,
        text,
        font,
        max_width,
    ):
        draw.text(
            (x, y),
            line,
            font=font,
            fill=fill,
        )
        y += line_height

    return y


def _new_pdf_page(title: str):
    from PIL import Image, ImageDraw

    page = Image.new(
        "RGB",
        (1240, 1754),
        "white",
    )
    draw = ImageDraw.Draw(
        page
    )
    font_logo = _load_font(
        42,
        bold=True,
    )
    font_small = _load_font(
        22,
    )
    draw.text(
        (90, 70),
        "CareerHub",
        font=font_logo,
        fill="#0f172a",
    )
    draw.text(
        (90, 122),
        title,
        font=font_small,
        fill="#6b7280",
    )
    draw.line(
        (90, 165, 1150, 165),
        fill="#2563eb",
        width=4,
    )

    return page, draw


def _render_structured_pdf(
    title: str,
    sections: list[dict],
) -> bytes | None:
    try:
        from PIL import Image
    except ImportError:
        return None

    pages = []
    page, draw = _new_pdf_page(
        title
    )
    y = 220
    margin_x = 90
    max_width = 1060
    font_h1 = _load_font(
        34,
        bold=True,
    )
    font_h2 = _load_font(
        27,
        bold=True,
    )
    font_body = _load_font(
        23,
    )

    def ensure_space(required: int):
        nonlocal page, draw, y

        if y + required <= 1650:
            return

        pages.append(
            page
        )
        page, draw = _new_pdf_page(
            title
        )
        y = 220

    ensure_space(
        90,
    )
    y = _draw_wrapped_text(
        draw,
        title,
        font_h1,
        margin_x,
        y,
        max_width,
        42,
        fill="#0f172a",
    )
    y += 32

    for section in sections or []:
        section_title = str(
            section.get("title", "")
        ).strip()
        body = str(
            section.get("body", "")
        ).strip()

        if not section_title and not body:
            continue

        ensure_space(
            150,
        )

        if section_title:
            y = _draw_wrapped_text(
                draw,
                section_title,
                font_h2,
                margin_x,
                y,
                max_width,
                34,
                fill="#2563eb",
            )
            y += 10

        if body:
            y = _draw_wrapped_text(
                draw,
                body,
                font_body,
                margin_x,
                y,
                max_width,
                31,
            )
            y += 30

    pages.append(
        page
    )
    buffer = BytesIO()
    first_page = pages[0]
    append_pages = pages[1:]
    first_page.save(
        buffer,
        format="PDF",
        save_all=True,
        append_images=append_pages,
        resolution=150,
    )

    return buffer.getvalue()


def render_application_pdf(html_content: str) -> bytes | None:
    html_for_pdf = prepare_html_for_pdf(
        html_content
    )

    for renderer in [
        _render_with_weasyprint,
        _render_with_pdfkit,
    ]:
        pdf_bytes = renderer(
            html_for_pdf
        )

        if pdf_bytes:
            _log_pdf_sizes(
                html_for_pdf,
                pdf_bytes,
            )

            return pdf_bytes

    _log_pdf_sizes(
        html_for_pdf,
        None,
    )

    return None


def _is_pdf_attachment(attachment: dict) -> bool:
    name = str(
        attachment.get("name")
        or attachment.get("archive_name")
        or ""
    ).lower()
    file_bytes = attachment.get("bytes") or b""

    return name.endswith(".pdf") or bytes(file_bytes).startswith(b"%PDF")


def _is_image_attachment(attachment: dict) -> bool:
    name = str(
        attachment.get("name")
        or attachment.get("archive_name")
        or ""
    ).lower()

    return name.endswith(
        (
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        )
    )


def _image_attachment_pdf_bytes(attachment: dict) -> bytes | None:
    try:
        from PIL import Image
    except ImportError:
        return None

    try:
        image = Image.open(
            BytesIO(
                bytes(
                    attachment.get("bytes") or b""
                )
            )
        )
    except Exception:
        return None

    if image.mode not in [
        "RGB",
        "L",
    ]:
        image = image.convert(
            "RGB"
        )

    buffer = BytesIO()

    try:
        image.save(
            buffer,
            format="PDF",
            resolution=150,
        )
    except Exception:
        return None

    return buffer.getvalue()


def _attachment_pdf_bytes(attachment: dict) -> bytes | None:
    if _is_pdf_attachment(
        attachment
    ):
        return bytes(
            attachment.get("bytes") or b""
        )

    if _is_image_attachment(
        attachment
    ):
        return _image_attachment_pdf_bytes(
            attachment
        )

    return None


def merge_pdf_documents(
    pdf_documents: list[bytes],
) -> bytes | None:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        return None

    writer = PdfWriter()

    for pdf_bytes in pdf_documents:
        if not pdf_bytes:
            continue

        try:
            reader = PdfReader(
                BytesIO(pdf_bytes)
            )
        except Exception:
            continue

        for page in reader.pages:
            writer.add_page(
                page
            )

    if not writer.pages:
        return None

    buffer = BytesIO()
    writer.write(
        buffer
    )

    return buffer.getvalue()


def render_final_application_pdf(
    html_content: str,
    attachments: list[dict] | None = None,
) -> bytes | None:
    base_pdf = render_application_pdf(
        html_content
    )

    if not base_pdf:
        return None

    pdf_documents = [
        base_pdf,
    ]

    for attachment in attachments or []:
        attachment_pdf = _attachment_pdf_bytes(
            attachment
        )

        if attachment_pdf:
            pdf_documents.append(
                attachment_pdf
            )

    merged_pdf = merge_pdf_documents(
        pdf_documents
    )

    if len(pdf_documents) > 1 and not merged_pdf:
        return None

    return merged_pdf or base_pdf


def render_application_summary_pdf(
    title: str,
    sections: list[dict],
    html_content: str = "",
) -> bytes | None:
    summary_title = title or "CareerHub PDF-Kurzfassung"
    pdf_bytes = _render_structured_pdf(
        summary_title,
        sections,
    )

    _log_pdf_sizes(
        html_content or summary_title,
        pdf_bytes,
    )

    return pdf_bytes
