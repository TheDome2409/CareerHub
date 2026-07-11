import base64
from io import BytesIO


MAX_PREVIEW_WIDTH = 1600
JPEG_QUALITY = 85


def _resize_to_max_width(image, max_width: int = MAX_PREVIEW_WIDTH):
    width, height = image.size

    if width <= max_width:
        return image

    ratio = max_width / width
    new_size = (
        max_width,
        max(1, int(height * ratio)),
    )

    return image.resize(
        new_size,
    )


def _image_to_jpeg_bytes(image) -> bytes:
    if image.mode not in [
        "RGB",
        "L",
    ]:
        image = image.convert(
            "RGB"
        )

    image = _resize_to_max_width(
        image
    )
    buffer = BytesIO()
    image.save(
        buffer,
        format="JPEG",
        quality=JPEG_QUALITY,
        optimize=True,
    )

    return buffer.getvalue()


def pdf_preview_jpeg_data_uri(file_bytes: bytes) -> str | None:
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        return None

    try:
        images = convert_from_bytes(
            file_bytes,
            dpi=160,
            first_page=1,
            last_page=1,
        )
    except Exception:
        return None

    if not images:
        return None

    jpeg_bytes = _image_to_jpeg_bytes(
        images[0]
    )
    encoded = base64.b64encode(
        jpeg_bytes
    ).decode(
        "ascii"
    )

    return f"data:image/jpeg;base64,{encoded}"
