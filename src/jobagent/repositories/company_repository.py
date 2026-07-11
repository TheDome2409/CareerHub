import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from jobagent.models.company import Company
from jobagent.models.company_document import CompanyDocument
from jobagent.models.company_evidence import CompanyEvidence
from jobagent.models.company_knowledge import CompanyKnowledge
from jobagent.models.company_knowledge_draft import CompanyKnowledgeDraft
from jobagent.models.company_profile_match import CompanyProfileMatch
from jobagent.models.company_profile import CompanyProfile
from jobagent.models.company_relationship import CompanyRelationship
from jobagent.models.company_source import CompanySource
from jobagent.services.companyhub_db_service import (
    get_connection,
    initialize_companyhub_db,
)


def _now() -> str:
    return datetime.now(
        timezone.utc
    ).replace(
        microsecond=0
    ).isoformat()


def normalize_company_name(name: str) -> str:
    value = str(name or "").strip().lower()
    value = re.sub(
        r"[^\w\s-]",
        " ",
        value,
    )
    value = re.sub(
        r"[_-]+",
        " ",
        value,
    )
    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    return value


def _json_list(values) -> str:
    return json.dumps(
        list(values or []),
        ensure_ascii=False,
    )


def _load_json_list(value: str | None) -> list[str]:
    if not value:
        return []

    try:
        data = json.loads(
            value
        )
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    return [
        str(item)
        for item in data
        if str(item).strip()
    ]


def _knowledge_list(values) -> list[str]:
    return [
        str(item.value if hasattr(item, "value") else item)
        for item in values or []
        if str(item.value if hasattr(item, "value") else item).strip()
    ]


def _knowledge_source_summary_payload(
    knowledge: CompanyKnowledge,
) -> str:
    return json.dumps(
        {
            "format": "company_knowledge_v1",
            "source_summary": knowledge.source_summary,
            "knowledge": knowledge.to_dict(),
        },
        ensure_ascii=False,
    )


def _knowledge_payload_from_source_summary(
    source_summary: str | None,
) -> dict | None:
    if not source_summary:
        return None

    try:
        data = json.loads(
            source_summary
        )
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    if data.get("format") != "company_knowledge_v1":
        return None

    knowledge = data.get("knowledge")

    if not isinstance(knowledge, dict):
        return None

    return knowledge


def _company_from_row(row) -> Company | None:
    if row is None:
        return None

    return Company(
        id=row["id"],
        name=row["name"],
        normalized_name=row["normalized_name"],
        website_url=row["website_url"],
        career_url=row["career_url"],
        industry=row["industry"],
        status=row["status"],
        ground_truth_available=bool(row["ground_truth_available"]),
        relationship_status=row["relationship_status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _company_profile_from_row(row) -> CompanyProfile | None:
    if row is None:
        return None

    return CompanyProfile(
        id=row["id"],
        company_id=row["company_id"],
        mission=row["mission"],
        vision=row["vision"],
        culture_summary=row["culture_summary"],
        technology_summary=row["technology_summary"],
        domains=_load_json_list(row["domains_json"]),
        work_models=_load_json_list(row["work_models_json"]),
        locations=_load_json_list(row["locations_json"]),
        kritis_relevance=bool(row["kritis_relevance"]),
        innovation_score=row["innovation_score"],
        source_summary=row["source_summary"],
        created_at=row["created_at"],
    )


def _source_type_value(source_type) -> str:
    return str(
        source_type.value if hasattr(source_type, "value") else source_type
    )


def _enum_value(value) -> str:
    return str(
        value.value if hasattr(value, "value") else value
    )


def _evidence_text_hash(text: str | None) -> str:
    normalized = re.sub(
        r"\s+",
        " ",
        str(text or "").strip(),
    )

    return hashlib.sha256(
        normalized.encode(
            "utf-8"
        )
    ).hexdigest()


def _company_source_from_row(row) -> CompanySource | None:
    if row is None:
        return None

    return CompanySource(
        id=row["id"],
        company_id=row["company_id"],
        source_type=row["source_type"],
        url=row["url"] or "",
        title=row["title"] or row["url"] or "Quelle",
        description=row["description"],
        enabled=bool(row["enabled"]),
        priority=row["priority"] if row["priority"] is not None else 3,
        last_checked=row["last_checked"] or row["fetched_at"],
        last_success=row["last_success"],
        etag=row["etag"],
        content_hash=row["content_hash"],
        notes=row["notes"],
        created_at=row["created_at"] or _now(),
    )


def _company_relationship_from_row(row) -> CompanyRelationship | None:
    if row is None:
        return None

    return CompanyRelationship(
        id=row["id"],
        company_id=row["company_id"],
        related_company_id=row["related_company_id"],
        related_company_name=row["related_company_name"],
        relationship_type=row["relationship_type"],
        direction=row["direction"] or "unknown",
        confidence=row["confidence"],
        source=row["source"],
        source_url=row["source_url"],
        evidence_text=row["evidence_text"],
        active=bool(row["active"]),
        observed_at=row["observed_at"],
        created_at=row["created_at"],
    )


def _company_document_from_row(row) -> CompanyDocument | None:
    if row is None:
        return None

    return CompanyDocument(
        id=row["id"],
        company_id=row["company_id"],
        source_id=row["source_id"],
        url=row["url"] or "",
        title=row["title"],
        content_type=row["content_type"],
        mime_type=row["mime_type"],
        charset=row["charset"],
        content_hash=row["content_hash"],
        content_text=row["content_text"] or "",
        status_code=row["status_code"],
        content_size=row["content_size"] or 0,
        etag=row["etag"],
        last_modified=row["last_modified_header"],
        fetched_at=row["fetched_at"],
        request_duration_ms=row["request_duration_ms"],
    )


def _company_evidence_from_row(row) -> CompanyEvidence | None:
    if row is None:
        return None

    return CompanyEvidence(
        id=row["id"],
        company_id=row["company_id"],
        document_id=row["document_id"],
        evidence_type=row["evidence_type"],
        title=row["title"],
        text=row["text"],
        source_type=row["source_type"] or "",
        source_name=row["source_name"] or "",
        source_url=row["source_url"] or "",
        section=row["section"],
        confidence=row["confidence"],
        language=row["language"],
        created_at=row["created_at"],
    )


def _company_knowledge_draft_from_row(row) -> CompanyKnowledgeDraft | None:
    if row is None:
        return None

    try:
        payload = json.loads(
            row["draft_json"] or "{}"
        )
    except json.JSONDecodeError:
        payload = {}

    payload.update(
        {
            "id": row["id"],
            "company_id": row["company_id"],
            "confidence": row["confidence"] or 0.0,
            "evidence_count": row["evidence_count"] or 0,
            "created_at": row["created_at"],
        }
    )

    return CompanyKnowledgeDraft.from_dict(
        payload
    )


def _company_profile_match_from_row(row) -> CompanyProfileMatch | None:
    if row is None:
        return None

    try:
        payload = json.loads(row["reasons_json"] or "{}")
    except json.JSONDecodeError:
        payload = {}

    if not isinstance(payload, dict):
        payload = {}

    details = payload.get("details")

    if not isinstance(details, dict):
        details = {}

    return CompanyProfileMatch(
        company_id=row["company_id"],
        profile_fingerprint=row["profile_fingerprint"],
        total_score=int(row["total_score"] or 0),
        mission_score=int(row["mission_score"] or 0),
        domain_score=int(details.get("domain_score") or row["culture_score"] or 0),
        technology_score=int(row["technology_score"] or 0),
        work_model_score=int(row["work_model_score"] or 0),
        kritis_score=int(details.get("kritis_score") or row["travel_score"] or 0),
        exclusion_score=int(details.get("exclusion_score") or 0),
        matched_concepts=list(details.get("matched_concepts") or []),
        missing_profile_preferences=list(
            details.get("missing_profile_preferences") or []
        ),
        risk_flags=list(details.get("risk_flags") or []),
        reasons=list(payload.get("reasons") or details.get("reasons") or []),
        confidence=float(details.get("confidence") or 0.0),
        created_at=row["created_at"],
    )


def _company_knowledge_from_row(row) -> CompanyKnowledge | None:
    if row is None:
        return None

    payload = _knowledge_payload_from_source_summary(
        row["source_summary"]
    )

    if payload is not None:
        payload.update(
            {
                "mission": row["mission"],
                "vision": row["vision"],
                "culture_summary": row["culture_summary"],
                "technology_summary": row["technology_summary"],
                "business_domains": _load_json_list(row["domains_json"]),
                "work_models": _load_json_list(row["work_models_json"]),
                "locations": _load_json_list(row["locations_json"]),
                "critical_infrastructure": bool(row["kritis_relevance"]),
                "innovation_score": row["innovation_score"],
                "created_at": row["created_at"],
            }
        )

        return CompanyKnowledge.from_dict(
            payload
        )

    return CompanyKnowledge(
        mission=row["mission"],
        vision=row["vision"],
        culture_summary=row["culture_summary"],
        technology_summary=row["technology_summary"],
        business_domains=_load_json_list(row["domains_json"]),
        work_models=_load_json_list(row["work_models_json"]),
        locations=_load_json_list(row["locations_json"]),
        critical_infrastructure=bool(row["kritis_relevance"]),
        innovation_score=row["innovation_score"],
        source_summary=row["source_summary"],
        created_at=row["created_at"],
    )


class CompanyRepository:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = initialize_companyhub_db(
            Path(db_path) if db_path else None
        )

    def create_company(
        self,
        name: str,
        website_url: str | None = None,
        career_url: str | None = None,
        industry: str | None = None,
        status: str = "active",
        ground_truth_available: bool = False,
        relationship_status: str | None = None,
    ) -> Company:
        normalized_name = normalize_company_name(
            name
        )
        timestamp = _now()

        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO companies (
                    name,
                    normalized_name,
                    website_url,
                    career_url,
                    industry,
                    status,
                    ground_truth_available,
                    relationship_status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    normalized_name,
                    website_url,
                    career_url,
                    industry,
                    status,
                    1 if ground_truth_available else 0,
                    relationship_status,
                    timestamp,
                    timestamp,
                ),
            )
            connection.commit()

            company_id = cursor.lastrowid

        return self.get_company_by_id(
            company_id
        )

    def get_company_by_id(self, company_id: int) -> Company | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM companies WHERE id = ?",
                (company_id,),
            ).fetchone()

        return _company_from_row(
            row
        )

    def get_company_by_normalized_name(
        self,
        normalized_name: str,
    ) -> Company | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM companies WHERE normalized_name = ?",
                (normalize_company_name(normalized_name),),
            ).fetchone()

        return _company_from_row(
            row
        )

    def list_companies(self) -> list[Company]:
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM companies ORDER BY name"
            ).fetchall()

        return [
            company
            for company in (
                _company_from_row(row)
                for row in rows
            )
            if company is not None
        ]

    def upsert_company(
        self,
        name: str,
        website_url: str | None = None,
        career_url: str | None = None,
        industry: str | None = None,
        status: str = "active",
        ground_truth_available: bool | None = None,
        relationship_status: str | None = None,
    ) -> Company:
        normalized_name = normalize_company_name(
            name
        )
        existing = self.get_company_by_normalized_name(
            normalized_name
        )

        if existing is None:
            return self.create_company(
                name=name,
                website_url=website_url,
                career_url=career_url,
                industry=industry,
                status=status,
                ground_truth_available=bool(ground_truth_available),
                relationship_status=relationship_status,
            )

        timestamp = _now()

        with get_connection(self.db_path) as connection:
            connection.execute(
                """
                UPDATE companies
                SET
                    name = ?,
                    website_url = COALESCE(?, website_url),
                    career_url = COALESCE(?, career_url),
                    industry = COALESCE(?, industry),
                    status = ?,
                    ground_truth_available = COALESCE(?, ground_truth_available),
                    relationship_status = COALESCE(?, relationship_status),
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    name,
                    website_url,
                    career_url,
                    industry,
                    status,
                    None
                    if ground_truth_available is None
                    else 1
                    if ground_truth_available
                    else 0,
                    relationship_status,
                    timestamp,
                    existing.id,
                ),
            )
            connection.commit()

        return self.get_company_by_id(
            existing.id
        )

    def mark_company_ground_truth_available(
        self,
        company_id: int,
        relationship_status: str | None = None,
        available: bool = True,
    ) -> Company | None:
        timestamp = _now()

        with get_connection(self.db_path) as connection:
            connection.execute(
                """
                UPDATE companies
                SET ground_truth_available = ?,
                    relationship_status = COALESCE(?, relationship_status),
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    1 if available else 0,
                    relationship_status,
                    timestamp,
                    company_id,
                ),
            )
            connection.commit()

        return self.get_company_by_id(
            company_id
        )

    def add_company_profile(
        self,
        company_id: int,
        mission: str | None = None,
        vision: str | None = None,
        culture_summary: str | None = None,
        technology_summary: str | None = None,
        domains: list[str] | None = None,
        work_models: list[str] | None = None,
        locations: list[str] | None = None,
        kritis_relevance: bool = False,
        innovation_score: int | None = None,
        source_summary: str | None = None,
    ) -> CompanyProfile:
        timestamp = _now()

        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO company_profiles (
                    company_id,
                    mission,
                    vision,
                    culture_summary,
                    technology_summary,
                    domains_json,
                    work_models_json,
                    locations_json,
                    kritis_relevance,
                    innovation_score,
                    source_summary,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    mission,
                    vision,
                    culture_summary,
                    technology_summary,
                    _json_list(domains),
                    _json_list(work_models),
                    _json_list(locations),
                    1 if kritis_relevance else 0,
                    innovation_score,
                    source_summary,
                    timestamp,
                ),
            )
            profile_id = cursor.lastrowid
            connection.commit()

        with get_connection(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM company_profiles WHERE id = ?",
                (profile_id,),
            ).fetchone()

        return _company_profile_from_row(
            row
        )

    def get_latest_company_profile(
        self,
        company_id: int,
    ) -> CompanyProfile | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT *
                FROM company_profiles
                WHERE company_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (company_id,),
            ).fetchone()

        return _company_profile_from_row(
            row
        )

    def _latest_company_profile_row(self, company_id: int):
        with get_connection(self.db_path) as connection:
            return connection.execute(
                """
                SELECT *
                FROM company_profiles
                WHERE company_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (company_id,),
            ).fetchone()

    def save_company_knowledge(
        self,
        company_id: int,
        knowledge: CompanyKnowledge,
    ) -> CompanyKnowledge:
        existing = self._latest_company_profile_row(
            company_id
        )

        if existing is None:
            return self._insert_company_knowledge(
                company_id,
                knowledge,
            )

        return self._update_company_knowledge_row(
            company_id,
            existing["id"],
            knowledge,
        )

    def load_company_knowledge(
        self,
        company_id: int,
    ) -> CompanyKnowledge | None:
        row = self._latest_company_profile_row(
            company_id
        )

        return _company_knowledge_from_row(
            row
        )

    def update_company_knowledge(
        self,
        company_id: int,
        knowledge: CompanyKnowledge,
    ) -> CompanyKnowledge:
        return self.save_company_knowledge(
            company_id,
            knowledge,
        )

    def delete_company_knowledge(
        self,
        company_id: int,
    ) -> None:
        with get_connection(self.db_path) as connection:
            connection.execute(
                "DELETE FROM company_profiles WHERE company_id = ?",
                (company_id,),
            )
            connection.commit()

    def _insert_company_knowledge(
        self,
        company_id: int,
        knowledge: CompanyKnowledge,
    ) -> CompanyKnowledge:
        timestamp = knowledge.created_at or _now()

        with get_connection(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO company_profiles (
                    company_id,
                    mission,
                    vision,
                    culture_summary,
                    technology_summary,
                    domains_json,
                    work_models_json,
                    locations_json,
                    kritis_relevance,
                    innovation_score,
                    source_summary,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    knowledge.mission,
                    knowledge.vision,
                    knowledge.culture_summary,
                    knowledge.technology_summary,
                    _json_list(_knowledge_list(knowledge.business_domains)),
                    _json_list(_knowledge_list(knowledge.work_models)),
                    _json_list(_knowledge_list(knowledge.locations)),
                    1 if knowledge.critical_infrastructure else 0,
                    knowledge.innovation_score,
                    _knowledge_source_summary_payload(knowledge),
                    timestamp,
                ),
            )
            connection.commit()

        return self.load_company_knowledge(
            company_id
        )

    def _update_company_knowledge_row(
        self,
        company_id: int,
        profile_id: int,
        knowledge: CompanyKnowledge,
    ) -> CompanyKnowledge:
        timestamp = knowledge.created_at or _now()

        with get_connection(self.db_path) as connection:
            connection.execute(
                """
                UPDATE company_profiles
                SET
                    mission = ?,
                    vision = ?,
                    culture_summary = ?,
                    technology_summary = ?,
                    domains_json = ?,
                    work_models_json = ?,
                    locations_json = ?,
                    kritis_relevance = ?,
                    innovation_score = ?,
                    source_summary = ?,
                    created_at = ?
                WHERE id = ?
                """,
                (
                    knowledge.mission,
                    knowledge.vision,
                    knowledge.culture_summary,
                    knowledge.technology_summary,
                    _json_list(_knowledge_list(knowledge.business_domains)),
                    _json_list(_knowledge_list(knowledge.work_models)),
                    _json_list(_knowledge_list(knowledge.locations)),
                    1 if knowledge.critical_infrastructure else 0,
                    knowledge.innovation_score,
                    _knowledge_source_summary_payload(knowledge),
                    timestamp,
                    profile_id,
                ),
            )
            connection.execute(
                """
                DELETE FROM company_profiles
                WHERE company_id = ? AND id != ?
                """,
                (
                    company_id,
                    profile_id,
                ),
            )
            connection.commit()

        return self.load_company_knowledge(
            company_id
        )

    def track_company(
        self,
        company_id: int,
        profile_fingerprint: str,
        priority: int = 3,
        notes: str | None = None,
    ) -> dict:
        timestamp = _now()

        with get_connection(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO tracked_companies (
                    company_id,
                    profile_fingerprint,
                    priority,
                    notes,
                    active,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(company_id, profile_fingerprint)
                DO UPDATE SET
                    priority = excluded.priority,
                    notes = excluded.notes,
                    active = 1,
                    updated_at = excluded.updated_at
                """,
                (
                    company_id,
                    profile_fingerprint,
                    priority,
                    notes,
                    timestamp,
                    timestamp,
                ),
            )
            row = connection.execute(
                """
                SELECT *
                FROM tracked_companies
                WHERE company_id = ? AND profile_fingerprint = ?
                """,
                (
                    company_id,
                    profile_fingerprint,
                ),
            ).fetchone()

        return dict(row) if row else {}

    def list_tracked_companies(
        self,
        profile_fingerprint: str,
    ) -> list[dict]:
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    tracked_companies.*,
                    companies.name,
                    companies.normalized_name,
                    companies.website_url,
                    companies.career_url,
                    companies.industry,
                    companies.status,
                    companies.ground_truth_available,
                    companies.relationship_status
                FROM tracked_companies
                JOIN companies ON companies.id = tracked_companies.company_id
                WHERE tracked_companies.profile_fingerprint = ?
                  AND tracked_companies.active = 1
                ORDER BY tracked_companies.priority ASC, companies.name ASC
                """,
                (profile_fingerprint,),
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    def deactivate_tracked_company(
        self,
        company_id: int,
        profile_fingerprint: str,
    ) -> dict:
        timestamp = _now()

        with get_connection(self.db_path) as connection:
            connection.execute(
                """
                UPDATE tracked_companies
                SET active = 0,
                    updated_at = ?
                WHERE company_id = ?
                  AND profile_fingerprint = ?
                """,
                (
                    timestamp,
                    company_id,
                    profile_fingerprint,
                ),
            )
            row = connection.execute(
                """
                SELECT *
                FROM tracked_companies
                WHERE company_id = ? AND profile_fingerprint = ?
                """,
                (
                    company_id,
                    profile_fingerprint,
                ),
            ).fetchone()
            connection.commit()

        return dict(row) if row else {}

    def add_company_source(
        self,
        company_id: int,
        source_type,
        url: str,
        title: str,
        description: str | None = None,
        enabled: bool = True,
        priority: int = 3,
        last_checked: str | None = None,
        last_success: str | None = None,
        etag: str | None = None,
        content_hash: str | None = None,
        notes: str | None = None,
    ) -> CompanySource:
        source_type_value = _source_type_value(
            source_type
        )
        timestamp = _now()

        with get_connection(self.db_path) as connection:
            existing = connection.execute(
                """
                SELECT id
                FROM company_sources
                WHERE company_id = ?
                  AND source_type = ?
                  AND url = ?
                """,
                (
                    company_id,
                    source_type_value,
                    url,
                ),
            ).fetchone()

            if existing:
                connection.execute(
                    """
                    UPDATE company_sources
                    SET title = ?,
                        description = COALESCE(?, description),
                        enabled = ?,
                        priority = ?,
                        last_checked = COALESCE(?, last_checked),
                        last_success = COALESCE(?, last_success),
                        etag = COALESCE(?, etag),
                        content_hash = COALESCE(?, content_hash),
                        notes = COALESCE(?, notes),
                        created_at = COALESCE(created_at, ?)
                    WHERE id = ?
                    """,
                    (
                        title,
                        description,
                        1 if enabled else 0,
                        priority,
                        last_checked,
                        last_success,
                        etag,
                        content_hash,
                        notes,
                        timestamp,
                        existing["id"],
                    ),
                )
                source_id = existing["id"]
            else:
                cursor = connection.execute(
                    """
                    INSERT INTO company_sources (
                        company_id,
                        source_type,
                        url,
                        title,
                        description,
                        enabled,
                        priority,
                        last_checked,
                        last_success,
                        etag,
                        content_hash,
                        notes,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        company_id,
                        source_type_value,
                        url,
                        title,
                        description,
                        1 if enabled else 0,
                        priority,
                        last_checked,
                        last_success,
                        etag,
                        content_hash,
                        notes,
                        timestamp,
                    ),
                )
                source_id = cursor.lastrowid

            row = connection.execute(
                "SELECT * FROM company_sources WHERE id = ?",
                (source_id,),
            ).fetchone()
            connection.commit()

        return _company_source_from_row(
            row
        )

    def update_company_source(
        self,
        source_id: int,
        **fields,
    ) -> CompanySource | None:
        allowed_fields = {
            "source_type",
            "url",
            "title",
            "description",
            "enabled",
            "priority",
            "last_checked",
            "last_success",
            "etag",
            "content_hash",
            "notes",
        }
        updates = []
        values = []

        for key, value in fields.items():
            if key not in allowed_fields:
                continue
            if key == "source_type":
                value = _source_type_value(
                    value
                )
            if key == "enabled":
                value = 1 if value else 0
            updates.append(
                f"{key} = ?"
            )
            values.append(
                value
            )

        if updates:
            values.append(
                source_id
            )
            with get_connection(self.db_path) as connection:
                connection.execute(
                    f"""
                    UPDATE company_sources
                    SET {", ".join(updates)}
                    WHERE id = ?
                    """,
                    tuple(values),
                )
                connection.commit()

        return self.get_company_source(
            source_id
        )

    def get_company_source(
        self,
        source_id: int,
    ) -> CompanySource | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM company_sources WHERE id = ?",
                (source_id,),
            ).fetchone()

        return _company_source_from_row(
            row
        )

    def list_company_sources(
        self,
        company_id: int,
        include_disabled: bool = True,
    ) -> list[CompanySource]:
        where = "WHERE company_id = ?"
        params = [company_id]

        if not include_disabled:
            where += " AND enabled = 1"

        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM company_sources
                {where}
                ORDER BY priority ASC, title ASC, id ASC
                """,
                tuple(params),
            ).fetchall()

        return [
            source
            for source in (
                _company_source_from_row(row)
                for row in rows
            )
            if source is not None
        ]

    def delete_company_source(
        self,
        source_id: int,
    ) -> None:
        with get_connection(self.db_path) as connection:
            connection.execute(
                "DELETE FROM company_sources WHERE id = ?",
                (source_id,),
            )
            connection.commit()

    def enable_company_source(
        self,
        source_id: int,
    ) -> CompanySource | None:
        return self.update_company_source(
            source_id,
            enabled=True,
        )

    def disable_company_source(
        self,
        source_id: int,
    ) -> CompanySource | None:
        return self.update_company_source(
            source_id,
            enabled=False,
        )

    def save_company_document(
        self,
        document: CompanyDocument,
    ) -> CompanyDocument:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO company_documents (
                    company_id,
                    source_id,
                    content_type,
                    mime_type,
                    charset,
                    url,
                    title,
                    status_code,
                    content_hash,
                    content_text,
                    content_size,
                    fetched_at,
                    last_modified_header,
                    etag,
                    request_duration_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document.company_id,
                    document.source_id,
                    document.content_type,
                    document.mime_type,
                    document.charset,
                    document.url,
                    document.title,
                    document.status_code,
                    document.content_hash,
                    document.content_text,
                    document.content_size,
                    document.fetched_at,
                    document.last_modified,
                    document.etag,
                    document.request_duration_ms,
                ),
            )
            document_id = cursor.lastrowid
            connection.execute(
                """
                UPDATE company_sources
                SET last_checked = ?,
                    last_success = CASE
                        WHEN ? BETWEEN 200 AND 299 THEN ?
                        ELSE last_success
                    END,
                    etag = COALESCE(?, etag),
                    content_hash = COALESCE(?, content_hash)
                WHERE id = ?
                """,
                (
                    document.fetched_at,
                    document.status_code,
                    document.fetched_at,
                    document.etag,
                    document.content_hash,
                    document.source_id,
                ),
            )
            row = connection.execute(
                "SELECT * FROM company_documents WHERE id = ?",
                (document_id,),
            ).fetchone()
            connection.commit()

        return _company_document_from_row(
            row
        )

    def load_latest_document(
        self,
        source_id: int,
    ) -> CompanyDocument | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT *
                FROM company_documents
                WHERE source_id = ?
                ORDER BY fetched_at DESC, id DESC
                LIMIT 1
                """,
                (source_id,),
            ).fetchone()

        return _company_document_from_row(
            row
        )

    def list_documents(
        self,
        company_id: int,
    ) -> list[CompanyDocument]:
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM company_documents
                WHERE company_id = ?
                ORDER BY fetched_at DESC, id DESC
                """,
                (company_id,),
            ).fetchall()

        return [
            document
            for document in (
                _company_document_from_row(row)
                for row in rows
            )
            if document is not None
        ]

    def add_company_relationship(
        self,
        company_id: int,
        related_company_name: str,
        relationship_type,
        related_company_id: int | None = None,
        direction="unknown",
        confidence: float | None = None,
        source: str | None = None,
        source_url: str | None = None,
        evidence_text: str | None = None,
        active: bool = True,
        observed_at: str | None = None,
    ) -> CompanyRelationship:
        timestamp = _now()
        observed = observed_at or timestamp

        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO company_relationships (
                    company_id,
                    related_company_id,
                    related_company_name,
                    relationship_type,
                    direction,
                    confidence,
                    source,
                    source_url,
                    evidence_text,
                    active,
                    observed_at,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    related_company_id,
                    related_company_name,
                    _enum_value(relationship_type),
                    _enum_value(direction),
                    confidence,
                    source,
                    source_url,
                    evidence_text,
                    1 if active else 0,
                    observed,
                    timestamp,
                ),
            )
            relationship_id = cursor.lastrowid
            row = connection.execute(
                "SELECT * FROM company_relationships WHERE id = ?",
                (relationship_id,),
            ).fetchone()
            connection.commit()

        return _company_relationship_from_row(
            row
        )

    def list_company_relationships(
        self,
        company_id: int,
        include_inactive: bool = False,
    ) -> list[CompanyRelationship]:
        where = "WHERE company_id = ?"
        params = [company_id]

        if not include_inactive:
            where += " AND active = 1"

        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM company_relationships
                {where}
                ORDER BY relationship_type ASC, related_company_name ASC, id ASC
                """,
                tuple(params),
            ).fetchall()

        return [
            relationship
            for relationship in (
                _company_relationship_from_row(row)
                for row in rows
            )
            if relationship is not None
        ]

    def get_company_relationships_by_type(
        self,
        company_id: int,
        relationship_type,
        include_inactive: bool = False,
    ) -> list[CompanyRelationship]:
        relationship_type_value = _enum_value(
            relationship_type
        )

        return [
            relationship
            for relationship in self.list_company_relationships(
                company_id,
                include_inactive=include_inactive,
            )
            if _enum_value(relationship.relationship_type) == relationship_type_value
        ]

    def deactivate_company_relationship(
        self,
        relationship_id: int,
    ) -> CompanyRelationship | None:
        with get_connection(self.db_path) as connection:
            connection.execute(
                """
                UPDATE company_relationships
                SET active = 0
                WHERE id = ?
                """,
                (relationship_id,),
            )
            row = connection.execute(
                "SELECT * FROM company_relationships WHERE id = ?",
                (relationship_id,),
            ).fetchone()
            connection.commit()

        return _company_relationship_from_row(
            row
        )

    def upsert_company_relationship(
        self,
        company_id: int,
        related_company_name: str,
        relationship_type,
        related_company_id: int | None = None,
        direction="unknown",
        confidence: float | None = None,
        source: str | None = None,
        source_url: str | None = None,
        evidence_text: str | None = None,
        active: bool = True,
        observed_at: str | None = None,
    ) -> CompanyRelationship:
        relationship_type_value = _enum_value(
            relationship_type
        )
        source_value = source or ""
        related_normalized = normalize_company_name(
            related_company_name
        )

        for existing in self.list_company_relationships(
            company_id,
            include_inactive=True,
        ):
            if (
                normalize_company_name(existing.related_company_name)
                == related_normalized
                and _enum_value(existing.relationship_type)
                == relationship_type_value
                and (existing.source or "") == source_value
            ):
                observed = observed_at or existing.observed_at

                with get_connection(self.db_path) as connection:
                    connection.execute(
                        """
                        UPDATE company_relationships
                        SET related_company_id = ?,
                            related_company_name = ?,
                            direction = ?,
                            confidence = ?,
                            source_url = ?,
                            evidence_text = ?,
                            active = ?,
                            observed_at = ?
                        WHERE id = ?
                        """,
                        (
                            related_company_id,
                            related_company_name,
                            _enum_value(direction),
                            confidence,
                            source_url,
                            evidence_text,
                            1 if active else 0,
                            observed,
                            existing.id,
                        ),
                    )
                    row = connection.execute(
                        "SELECT * FROM company_relationships WHERE id = ?",
                        (existing.id,),
                    ).fetchone()
                    connection.commit()

                return _company_relationship_from_row(
                    row
                )

        return self.add_company_relationship(
            company_id=company_id,
            related_company_id=related_company_id,
            related_company_name=related_company_name,
            relationship_type=relationship_type,
            direction=direction,
            confidence=confidence,
            source=source,
            source_url=source_url,
            evidence_text=evidence_text,
            active=active,
            observed_at=observed_at,
        )

    def save_company_evidence(
        self,
        evidence: CompanyEvidence,
    ) -> CompanyEvidence:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO company_evidence (
                    company_id,
                    document_id,
                    evidence_type,
                    title,
                    text,
                    source_type,
                    source_name,
                    source_url,
                    section,
                    confidence,
                    language,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence.company_id,
                    evidence.document_id,
                    _enum_value(evidence.evidence_type),
                    evidence.title,
                    evidence.text,
                    evidence.source_type,
                    evidence.source_name,
                    evidence.source_url,
                    evidence.section,
                    evidence.confidence,
                    evidence.language,
                    evidence.created_at,
                ),
            )
            evidence_id = cursor.lastrowid
            row = connection.execute(
                "SELECT * FROM company_evidence WHERE id = ?",
                (evidence_id,),
            ).fetchone()
            connection.commit()

        return _company_evidence_from_row(
            row
        )

    def list_company_evidence(
        self,
        company_id: int,
    ) -> list[CompanyEvidence]:
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM company_evidence
                WHERE company_id = ?
                ORDER BY created_at DESC, id DESC
                """,
                (company_id,),
            ).fetchall()

        return [
            evidence
            for evidence in (
                _company_evidence_from_row(row)
                for row in rows
            )
            if evidence is not None
        ]

    def list_company_evidence_by_type(
        self,
        company_id: int,
        evidence_type,
    ) -> list[CompanyEvidence]:
        evidence_type_value = _enum_value(
            evidence_type
        )

        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM company_evidence
                WHERE company_id = ?
                  AND evidence_type = ?
                ORDER BY created_at DESC, id DESC
                """,
                (
                    company_id,
                    evidence_type_value,
                ),
            ).fetchall()

        return [
            evidence
            for evidence in (
                _company_evidence_from_row(row)
                for row in rows
            )
            if evidence is not None
        ]

    def find_existing_evidence(
        self,
        company_id: int,
        evidence_type,
        text_hash: str,
    ) -> CompanyEvidence | None:
        evidence_type_value = _enum_value(
            evidence_type
        )

        for evidence in self.list_company_evidence_by_type(
            company_id,
            evidence_type_value,
        ):
            if _evidence_text_hash(
                evidence.text
            ) == text_hash:
                return evidence

        return None

    def upsert_company_evidence(
        self,
        evidence: CompanyEvidence,
    ) -> tuple[CompanyEvidence, bool]:
        existing = self.find_existing_evidence(
            company_id=evidence.company_id,
            evidence_type=evidence.evidence_type,
            text_hash=_evidence_text_hash(
                evidence.text
            ),
        )

        if existing is not None:
            return existing, False

        return self.save_company_evidence(
            evidence
        ), True

    def delete_company_evidence(
        self,
        evidence_id: int,
    ) -> None:
        with get_connection(self.db_path) as connection:
            connection.execute(
                "DELETE FROM company_evidence WHERE id = ?",
                (evidence_id,),
            )
            connection.commit()

    def save_company_knowledge_draft(
        self,
        draft: CompanyKnowledgeDraft,
    ) -> CompanyKnowledgeDraft:
        payload = draft.to_dict()
        payload.pop(
            "id",
            None,
        )

        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO company_knowledge_drafts (
                    company_id,
                    draft_json,
                    confidence,
                    evidence_count,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    draft.company_id,
                    json.dumps(
                        payload,
                        ensure_ascii=False,
                    ),
                    draft.confidence,
                    draft.evidence_count,
                    draft.created_at,
                ),
            )
            draft_id = cursor.lastrowid
            row = connection.execute(
                "SELECT * FROM company_knowledge_drafts WHERE id = ?",
                (draft_id,),
            ).fetchone()
            connection.commit()

        return _company_knowledge_draft_from_row(
            row
        )

    def load_latest_company_knowledge_draft(
        self,
        company_id: int,
    ) -> CompanyKnowledgeDraft | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT *
                FROM company_knowledge_drafts
                WHERE company_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (company_id,),
            ).fetchone()

        return _company_knowledge_draft_from_row(
            row
        )

    def list_company_knowledge_drafts(
        self,
        company_id: int,
    ) -> list[CompanyKnowledgeDraft]:
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM company_knowledge_drafts
                WHERE company_id = ?
                ORDER BY created_at DESC, id DESC
                """,
                (company_id,),
            ).fetchall()

        return [
            draft
            for draft in (
                _company_knowledge_draft_from_row(row)
                for row in rows
            )
            if draft is not None
        ]

    def save_company_profile_match(
        self,
        match: CompanyProfileMatch,
    ) -> CompanyProfileMatch:
        payload = {
            "format": "company_profile_match_v1",
            "reasons": match.reasons,
            "details": {
                "domain_score": match.domain_score,
                "kritis_score": match.kritis_score,
                "exclusion_score": match.exclusion_score,
                "matched_concepts": match.matched_concepts,
                "missing_profile_preferences": match.missing_profile_preferences,
                "risk_flags": match.risk_flags,
                "confidence": match.confidence,
                "reasons": match.reasons,
            },
        }

        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO company_match_results (
                    company_id,
                    profile_fingerprint,
                    mission_score,
                    culture_score,
                    technology_score,
                    work_model_score,
                    travel_score,
                    total_score,
                    reasons_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    match.company_id,
                    match.profile_fingerprint,
                    match.mission_score,
                    match.domain_score,
                    match.technology_score,
                    match.work_model_score,
                    match.kritis_score,
                    match.total_score,
                    json.dumps(payload, ensure_ascii=False),
                    match.created_at,
                ),
            )
            row = connection.execute(
                "SELECT * FROM company_match_results WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
            connection.commit()

        return _company_profile_match_from_row(row)

    def load_latest_company_profile_match(
        self,
        company_id: int,
        profile_fingerprint: str,
    ) -> CompanyProfileMatch | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT *
                FROM company_match_results
                WHERE company_id = ? AND profile_fingerprint = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (
                    company_id,
                    profile_fingerprint,
                ),
            ).fetchone()

        return _company_profile_match_from_row(row)

    def list_company_profile_matches(
        self,
        profile_fingerprint: str,
    ) -> list[CompanyProfileMatch]:
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM company_match_results
                WHERE profile_fingerprint = ?
                ORDER BY created_at DESC, id DESC
                """,
                (profile_fingerprint,),
            ).fetchall()

        return [
            match
            for match in (
                _company_profile_match_from_row(row)
                for row in rows
            )
            if match is not None
        ]
