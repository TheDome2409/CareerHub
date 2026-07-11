from jobagent.models.document_model import (
    Document,
    DocumentBlock,
    DocumentSection,
)
from jobagent.services.application_html_service import (
    attachment_display_title,
)


def _text(value) -> str:
    return str(value or "").strip()


def _non_empty(values) -> list[str]:
    return [
        _text(value)
        for value in values or []
        if _text(value)
    ]


def _attachment_items(
    attachments: list[dict] | None,
    curated_attachment_overview: list[dict] | None = None,
    include_fallback: bool = False,
) -> list[dict]:
    if curated_attachment_overview:
        return [
            {
                "title": _text(item.get("title") or item.get("name")),
                "description": _text(
                    item.get("description") or item.get("reason")
                ),
            }
            for item in curated_attachment_overview
            if _text(item.get("title") or item.get("name"))
        ]

    items = []

    for index, attachment in enumerate(
        attachments or [],
        start=1,
    ):
        title = attachment_display_title(
            attachment,
            index,
        )

        if title.startswith("Anlage "):
            continue

        if title in {
            "Zeugnis / Nachweis",
            "Zertifikat",
            "Projektunterlage",
        }:
            continue

        items.append(
            {
                "title": title,
                "description": _text(attachment.get("reason")),
            }
        )

    if items or not include_fallback:
        return items

    return [
        {
            "title": "Anlagen werden separat beigefuegt",
            "description": (
                "Es wurde noch keine kuratierte Anlagenübersicht "
                "erzeugt."
            ),
        }
    ]


def build_application_document(
    title: str = "Bewerbungsmappe",
    subtitle: str | None = None,
    cover_letter: str = "",
    profile_summary: str = "",
    profile_tags: list[str] | set[str] | None = None,
    candidate_insights: list[dict] | list[str] | None = None,
    context_resume: str = "",
    careerhub_project: str = "",
    attachments: list[dict] | None = None,
    curated_attachment_overview: list[dict] | None = None,
    include_attachment_fallback: bool = False,
) -> Document:
    sections = [
        DocumentSection(
            title="Anschreiben",
            kind="cover_letter",
            blocks=[
                DocumentBlock(
                    kind="paragraph",
                    content=cover_letter,
                )
            ],
        ),
        DocumentSection(
            title="Profil und Kompetenzprofil",
            kind="profile",
            page_break_before=True,
            blocks=[
                DocumentBlock(
                    kind="paragraph",
                    title="Profil",
                    content=profile_summary,
                ),
                DocumentBlock(
                    kind="skill_grid",
                    title="Kompetenzen",
                    items=sorted(
                        _non_empty(profile_tags)
                    ),
                ),
            ],
        ),
    ]

    if candidate_insights:
        sections.append(
            DocumentSection(
                title="Candidate Insights",
                kind="candidate_insights",
                blocks=[
                    DocumentBlock(
                        kind="card_list",
                        items=candidate_insights,
                    )
                ],
            )
        )

    if _text(context_resume):
        sections.append(
            DocumentSection(
                title="Lebenslauf",
                kind="resume",
                blocks=[
                    DocumentBlock(
                        kind="paragraph",
                        content=context_resume,
                    )
                ],
            )
        )

    if _text(careerhub_project):
        sections.append(
            DocumentSection(
                title="CareerHub-Projektvorstellung",
                kind="project_context",
                blocks=[
                    DocumentBlock(
                        kind="paragraph",
                        content=careerhub_project,
                    )
                ],
            )
        )

    attachment_items = _attachment_items(
        attachments,
        curated_attachment_overview,
        include_fallback=include_attachment_fallback,
    )

    if attachment_items:
        sections.append(
            DocumentSection(
                title="Anlagenübersicht",
                kind="attachments",
                page_break_before=True,
                blocks=[
                    DocumentBlock(
                        kind="attachment_overview",
                        items=attachment_items,
                    )
                ],
            )
        )

    return Document(
        title=title,
        subtitle=subtitle,
        metadata={
            "footer_note": "Erstellt mit CareerHub",
        },
        sections=sections,
    )
