from jobagent.models.company_evidence import CompanyEvidence, EvidenceType
from jobagent.models.document_processing_result import DocumentProcessingResult
from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.company_evidence_service import (
    delete_company_evidence,
    extract_evidence,
    list_company_evidence,
    list_company_evidence_by_type,
    save_company_evidence,
)
from jobagent.services.document_processing_service import process_document
from jobagent.services.companyhub_db_service import get_connection


def _result(text: str) -> DocumentProcessingResult:
    return DocumentProcessingResult(
        source_type="html",
        mime_type="text/html",
        original_size=len(
            text.encode("utf-8")
        ),
        processed_size=len(
            text.encode("utf-8")
        ),
        title="Company Website",
        clean_text=text,
        metadata={
            "document_id": 7,
            "source_type": "company_website",
            "source_name": "Website",
            "source_url": "https://example.test",
        },
        processing_steps=[
            "loaded",
            "cleanup",
        ],
    )


def test_extract_mission_section():
    company = {
        "id": 1,
    }
    result = _result(
        "Mission\nWir digitalisieren öffentliche Verwaltung."
    )

    evidence = extract_evidence(
        company,
        result,
    )

    assert len(evidence) == 1
    assert evidence[0].evidence_type == EvidenceType.MISSION
    assert evidence[0].title == "Mission"
    assert evidence[0].text == "Wir digitalisieren öffentliche Verwaltung."
    assert evidence[0].document_id == 7
    assert evidence[0].source_url == "https://example.test"


def test_extract_vision_and_benefits_sections():
    evidence = extract_evidence(
        {
            "id": 1,
        },
        _result(
            """
            Vision
            Eine moderne digitale Infrastruktur.

            Benefits
            Flexible Arbeitsmodelle und Weiterbildung.
            """
        ),
    )

    assert [
        item.evidence_type
        for item in evidence
    ] == [
        EvidenceType.VISION,
        EvidenceType.BENEFIT,
    ]
    assert evidence[1].text == "Flexible Arbeitsmodelle und Weiterbildung."


def test_extract_empty_text_returns_no_evidence():
    evidence = extract_evidence(
        {
            "id": 1,
        },
        _result(
            ""
        ),
    )

    assert evidence == []


def test_extract_html_without_clear_headings_creates_fallback_other_evidence():
    result = process_document(
        """
        <html>
          <body>
            <main>
              <p>DB InfraGO betreibt und entwickelt die Eisenbahninfrastruktur.</p>
              <p>Wir verbinden Menschen und Märkte in Deutschland.</p>
            </main>
          </body>
        </html>
        """,
        mime_type="text/html",
        title="DB InfraGO Website",
        metadata={
            "document_id": 9,
            "source_type": "company_website",
            "source_name": "Website",
            "source_url": "https://example.test",
        },
    )

    evidence = extract_evidence(
        {
            "id": 1,
        },
        result,
    )

    assert len(evidence) >= 1
    assert evidence[0].evidence_type in {
        EvidenceType.KRITIS,
        EvidenceType.OTHER,
    }
    assert "Eisenbahninfrastruktur" in evidence[0].text
    assert evidence[0].document_id == 9


def test_extract_html_with_career_and_benefits_keywords():
    result = process_document(
        """
        <html>
          <body>
            <h2>Karriere</h2>
            <p>Arbeiten bei uns bedeutet Jobs mit Verantwortung.</p>
            <h2>Benefits</h2>
            <p>Flexible Arbeitsmodelle und Weiterbildung.</p>
          </body>
        </html>
        """,
        mime_type="text/html",
        title="Karriere",
        metadata={
            "document_id": 10,
            "source_type": "career_page",
            "source_name": "Karriere",
            "source_url": "https://example.test/jobs",
        },
    )

    evidence = extract_evidence(
        {
            "id": 1,
        },
        result,
    )

    assert [
        item.evidence_type
        for item in evidence
    ] == [
        EvidenceType.CAREER,
        EvidenceType.BENEFIT,
    ]
    assert "Flexible Arbeitsmodelle" in evidence[1].text


def test_extract_multiple_sections_including_other():
    evidence = extract_evidence(
        {
            "id": 1,
        },
        _result(
            """
            Willkommen bei Example.
            Vision
            Wir bauen digitale Services.
            Standorte
            Hannover und Berlin.
            """
        ),
    )

    assert [
        item.evidence_type
        for item in evidence
    ] == [
        EvidenceType.OTHER,
        EvidenceType.VISION,
        EvidenceType.LOCATION,
    ]


def test_company_evidence_repository_roundtrip(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )
    company = repository.upsert_company(
        "Dataport"
    )
    evidence = CompanyEvidence(
        company_id=company.id,
        evidence_type=EvidenceType.CAREER,
        title="Karriere",
        text="Wir suchen Menschen für digitale Verwaltung.",
        source_type="career_page",
        source_name="Karriere",
        source_url="https://example.test/jobs",
        section="Karriere",
        confidence=0.75,
    )

    saved = save_company_evidence(
        evidence,
        repository=repository,
    )
    listed = list_company_evidence(
        company.id,
        repository=repository,
    )
    career = list_company_evidence_by_type(
        company.id,
        EvidenceType.CAREER,
        repository=repository,
    )

    assert saved.id is not None
    assert len(listed) == 1
    assert listed[0].text == evidence.text
    assert len(career) == 1
    assert career[0].evidence_type == "career"

    delete_company_evidence(
        saved.id,
        repository=repository,
    )

    assert list_company_evidence(
        company.id,
        repository=repository,
    ) == []


def test_company_evidence_table_exists(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )

    with get_connection(repository.db_path) as connection:
        row = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'company_evidence'
            """
        ).fetchone()

    assert row["name"] == "company_evidence"
