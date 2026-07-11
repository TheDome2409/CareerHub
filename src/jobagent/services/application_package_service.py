import zipfile
from io import BytesIO


def application_zip_bytes(
    html_content: str,
    attachments: list[dict],
    html_name: str = "bewerbungsmappe.html",
    extra_files: list[dict] | None = None,
) -> bytes:
    buffer = BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            html_name,
            html_content,
        )

        used_names = set()

        for attachment in attachments or []:
            archive_name = attachment["archive_name"]
            candidate = archive_name
            counter = 2

            while candidate.lower() in used_names:
                stem, dot, suffix = archive_name.rpartition(".")

                if dot:
                    candidate = f"{stem}-{counter}.{suffix}"
                else:
                    candidate = f"{archive_name}-{counter}"

                counter += 1

            used_names.add(candidate.lower())
            archive.writestr(
                f"anlagen/{candidate}",
                attachment["bytes"],
            )

        for item in extra_files or []:
            name = item.get("name")
            content = item.get("bytes")

            if not name or content is None:
                continue

            archive.writestr(
                name,
                content,
            )

    return buffer.getvalue()
