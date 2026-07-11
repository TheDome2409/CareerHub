import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from jobagent.models.skill_registry import (
    SkillRegistryConflict,
    SkillRegistryEntry,
    utc_now,
)
from jobagent.repositories import YamlTaxonomyRepository
from jobagent.services.companyhub_db_service import (
    get_connection,
    get_companyhub_db_path,
    initialize_companyhub_db,
)
from jobagent.services.skill_candidate_domain_service import (
    normalize_domain_text,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SKILL_TAXONOMY_FILE = PROJECT_ROOT / "config" / "skill_taxonomy.yaml"


DEFAULT_SKILL_TYPE = "skill"
ACTIVE_STATUSES = {
    "active",
}


class SkillRegistryError(Exception):
    pass


class SkillRegistryConflictError(SkillRegistryError):
    def __init__(self, conflict: SkillRegistryConflict):
        super().__init__(
            conflict.reason
        )
        self.conflict = conflict


@dataclass(frozen=True)
class SkillRegistrySaveResult:
    entry: SkillRegistryEntry | None
    action: str
    conflict: SkillRegistryConflict | None = None
    previous_entry: SkillRegistryEntry | None = None


def normalize_skill_registry_key(value: str | None) -> str:
    normalized = normalize_domain_text(
        value or ""
    )
    normalized = normalized.replace(
        "landingzone",
        "landing zone",
    )
    normalized = re.sub(
        r"[^a-z0-9]+",
        " ",
        normalized,
    )
    tokens = []

    for token in normalized.split():
        if len(token) > 3 and token.endswith("s"):
            token = token[:-1]
        tokens.append(token)

    return "".join(tokens)


def _type_value(value: str | None) -> str:
    return str(value or DEFAULT_SKILL_TYPE).strip().lower() or DEFAULT_SKILL_TYPE


def _display_name(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip(),
    )


def _row_to_entry(connection: sqlite3.Connection, row) -> SkillRegistryEntry | None:
    if row is None:
        return None

    alias_rows = connection.execute(
        """
        SELECT alias
        FROM skill_registry_aliases
        WHERE skill_id = ?
        ORDER BY id
        """,
        (row["id"],),
    ).fetchall()

    return SkillRegistryEntry(
        id=row["id"],
        canonical_name=row["canonical_name"],
        display_name=row["display_name"],
        type=row["type"],
        aliases=[
            alias_row["alias"]
            for alias_row in alias_rows
        ],
        description=row["description"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        created_by=row["created_by"],
        source=row["source"],
        status=row["status"],
    )


def _insert_alias(
    connection: sqlite3.Connection,
    skill_id: int,
    alias: str,
    skill_type: str,
) -> None:
    alias = _display_name(
        alias
    )

    if not alias:
        return

    connection.execute(
        """
        INSERT OR IGNORE INTO skill_registry_aliases (
            skill_id,
            alias,
            normalized_alias,
            type,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            skill_id,
            alias,
            normalize_skill_registry_key(alias),
            skill_type,
            utc_now(),
        ),
    )


def initialize_skill_registry(db_path: str | Path | None = None) -> Path:
    return initialize_companyhub_db(
        Path(db_path) if db_path else None
    )


def _snapshot_registry(path: Path) -> tuple[list[dict], list[dict]]:
    with get_connection(path) as connection:
        skill_rows = [
            dict(row)
            for row in connection.execute(
                """
                SELECT *
                FROM skill_registry
                ORDER BY id
                """
            ).fetchall()
        ]
        alias_rows = [
            dict(row)
            for row in connection.execute(
                """
                SELECT *
                FROM skill_registry_aliases
                ORDER BY id
                """
            ).fetchall()
        ]

    return skill_rows, alias_rows


def _restore_registry_snapshot(
    path: Path,
    snapshot: tuple[list[dict], list[dict]],
) -> None:
    skill_rows, alias_rows = snapshot

    with get_connection(path) as connection:
        try:
            connection.execute(
                "BEGIN"
            )
            connection.execute(
                "DELETE FROM skill_registry_aliases"
            )
            connection.execute(
                "DELETE FROM skill_registry"
            )
            for row in skill_rows:
                connection.execute(
                    """
                    INSERT INTO skill_registry (
                        id,
                        canonical_name,
                        canonical_key,
                        display_name,
                        type,
                        description,
                        created_at,
                        updated_at,
                        created_by,
                        source,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["id"],
                        row["canonical_name"],
                        row["canonical_key"],
                        row["display_name"],
                        row["type"],
                        row["description"],
                        row["created_at"],
                        row["updated_at"],
                        row["created_by"],
                        row["source"],
                        row["status"],
                    ),
                )
            for row in alias_rows:
                connection.execute(
                    """
                    INSERT INTO skill_registry_aliases (
                        id,
                        skill_id,
                        alias,
                        normalized_alias,
                        type,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["id"],
                        row["skill_id"],
                        row["alias"],
                        row["normalized_alias"],
                        row["type"],
                        row["created_at"],
                    ),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def get_skill_by_id(
    skill_id: int,
    db_path: str | Path | None = None,
) -> SkillRegistryEntry | None:
    path = initialize_skill_registry(
        db_path
    )

    with get_connection(path) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM skill_registry
            WHERE id = ?
            """,
            (skill_id,),
        ).fetchone()

        return _row_to_entry(
            connection,
            row,
        )


def find_skill(
    value: str,
    skill_type: str | None = None,
    db_path: str | Path | None = None,
) -> SkillRegistryEntry | None:
    key = normalize_skill_registry_key(
        value
    )

    if not key:
        return None

    path = initialize_skill_registry(
        db_path
    )
    params = [
        key,
    ]
    type_filter = ""

    if skill_type:
        type_filter = "AND type = ?"
        params.append(
            _type_value(skill_type)
        )

    with get_connection(path) as connection:
        row = connection.execute(
            f"""
            SELECT *
            FROM skill_registry
            WHERE canonical_key = ?
            {type_filter}
            ORDER BY id
            LIMIT 1
            """,
            params,
        ).fetchone()

        if row is None:
            row = connection.execute(
                f"""
                SELECT sr.*
                FROM skill_registry sr
                JOIN skill_registry_aliases alias
                    ON alias.skill_id = sr.id
                WHERE alias.normalized_alias = ?
                {type_filter.replace("type", "sr.type")}
                ORDER BY sr.id
                LIMIT 1
                """,
                params,
            ).fetchone()

        return _row_to_entry(
            connection,
            row,
        )


def _find_conflicting_skill(
    connection: sqlite3.Connection,
    value: str,
    skill_type: str,
):
    key = normalize_skill_registry_key(
        value
    )

    if not key:
        return None

    return connection.execute(
        """
        SELECT sr.*
        FROM skill_registry sr
        LEFT JOIN skill_registry_aliases alias
            ON alias.skill_id = sr.id
        WHERE (sr.canonical_key = ? OR alias.normalized_alias = ?)
            AND sr.type != ?
        ORDER BY sr.id
        LIMIT 1
        """,
        (
            key,
            key,
            skill_type,
        ),
    ).fetchone()


def _find_matching_skill_row(
    connection: sqlite3.Connection,
    value: str,
    skill_type: str,
):
    key = normalize_skill_registry_key(
        value
    )

    if not key:
        return None

    row = connection.execute(
        """
        SELECT *
        FROM skill_registry
        WHERE canonical_key = ?
            AND type = ?
        ORDER BY id
        LIMIT 1
        """,
        (
            key,
            skill_type,
        ),
    ).fetchone()

    if row is not None:
        return row

    return connection.execute(
        """
        SELECT sr.*
        FROM skill_registry sr
        JOIN skill_registry_aliases alias
            ON alias.skill_id = sr.id
        WHERE alias.normalized_alias = ?
            AND sr.type = ?
        ORDER BY sr.id
        LIMIT 1
        """,
        (
            key,
            skill_type,
        ),
    ).fetchone()


def save_skill(
    canonical_name: str,
    skill_type: str = DEFAULT_SKILL_TYPE,
    aliases: list[str] | None = None,
    display_name: str | None = None,
    description: str | None = None,
    created_by: str = "system",
    source: str = "unknown",
    status: str = "active",
    db_path: str | Path | None = None,
) -> SkillRegistrySaveResult:
    canonical_name = _display_name(
        canonical_name
    )
    skill_type = _type_value(
        skill_type
    )

    if not canonical_name:
        raise ValueError(
            "canonical_name must not be empty"
        )

    alias_values = [
        _display_name(alias)
        for alias in aliases or []
        if _display_name(alias)
    ]
    alias_values.append(
        canonical_name
    )
    canonical_key = normalize_skill_registry_key(
        canonical_name
    )
    path = initialize_skill_registry(
        db_path
    )

    with get_connection(path) as connection:
        try:
            connection.execute(
                "BEGIN"
            )
            for value in alias_values:
                conflict_row = _find_conflicting_skill(
                    connection,
                    value,
                    skill_type,
                )
                if conflict_row is not None:
                    conflict = SkillRegistryConflict(
                        raw_name=value,
                        canonical_name=canonical_name,
                        requested_type=skill_type,
                        existing_type=conflict_row["type"],
                        existing_skill_id=conflict_row["id"],
                        reason=(
                            "Skill name or alias already exists with a "
                            "different type."
                        ),
                    )
                    connection.rollback()
                    return SkillRegistrySaveResult(
                        entry=None,
                        action="conflict",
                        conflict=conflict,
                    )

            existing_row = _find_matching_skill_row(
                connection,
                canonical_name,
                skill_type,
            )

            if existing_row is None:
                for alias in alias_values:
                    existing_row = _find_matching_skill_row(
                        connection,
                        alias,
                        skill_type,
                    )
                    if existing_row is not None:
                        break

            existing = _row_to_entry(
                connection,
                existing_row,
            )

            now = utc_now()

            if existing:
                previous_entry = existing
                connection.execute(
                    """
                    UPDATE skill_registry
                    SET display_name = ?,
                        description = COALESCE(?, description),
                        updated_at = ?,
                        source = ?,
                        status = ?
                    WHERE id = ?
                    """,
                    (
                        display_name or existing.display_name,
                        description,
                        now,
                        source or existing.source,
                        status or existing.status,
                        existing.id,
                    ),
                )
                skill_id = int(existing.id)
                action = "merged"
            else:
                previous_entry = None
                cursor = connection.execute(
                    """
                    INSERT INTO skill_registry (
                        canonical_name,
                        canonical_key,
                        display_name,
                        type,
                        description,
                        created_at,
                        updated_at,
                        created_by,
                        source,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        canonical_name,
                        canonical_key,
                        display_name or canonical_name,
                        skill_type,
                        description,
                        now,
                        now,
                        created_by,
                        source,
                        status,
                    ),
                )
                skill_id = int(cursor.lastrowid)
                action = "created"

            for alias in alias_values:
                _insert_alias(
                    connection,
                    skill_id,
                    alias,
                    skill_type,
                )

            connection.commit()

            return SkillRegistrySaveResult(
                entry=get_skill_by_id(
                    skill_id,
                    path,
                ),
                action=action,
                previous_entry=previous_entry,
            )
        except Exception:
            connection.rollback()
            raise


def delete_skill(
    skill_id: int,
    db_path: str | Path | None = None,
) -> None:
    path = initialize_skill_registry(
        db_path
    )

    with get_connection(path) as connection:
        try:
            connection.execute(
                "BEGIN"
            )
            connection.execute(
                """
                DELETE FROM skill_registry_aliases
                WHERE skill_id = ?
                """,
                (
                    skill_id,
                ),
            )
            connection.execute(
                """
                DELETE FROM skill_registry
                WHERE id = ?
                """,
                (
                    skill_id,
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def restore_skill(
    entry: SkillRegistryEntry,
    db_path: str | Path | None = None,
) -> None:
    if entry.id is None:
        return

    path = initialize_skill_registry(
        db_path
    )

    with get_connection(path) as connection:
        try:
            connection.execute(
                "BEGIN"
            )
            connection.execute(
                """
                UPDATE skill_registry
                SET canonical_name = ?,
                    canonical_key = ?,
                    display_name = ?,
                    type = ?,
                    description = ?,
                    updated_at = ?,
                    created_by = ?,
                    source = ?,
                    status = ?
                WHERE id = ?
                """,
                (
                    entry.canonical_name,
                    normalize_skill_registry_key(entry.canonical_name),
                    entry.display_name,
                    entry.type,
                    entry.description,
                    entry.updated_at,
                    entry.created_by,
                    entry.source,
                    entry.status,
                    entry.id,
                ),
            )
            connection.execute(
                """
                DELETE FROM skill_registry_aliases
                WHERE skill_id = ?
                """,
                (
                    entry.id,
                ),
            )
            for alias in entry.aliases:
                _insert_alias(
                    connection,
                    entry.id,
                    alias,
                    entry.type,
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def rollback_skill_registry_write(
    result: SkillRegistrySaveResult,
    db_path: str | Path | None = None,
) -> None:
    if result.action == "created" and result.entry and result.entry.id:
        delete_skill(
            result.entry.id,
            db_path,
        )
        return

    if result.action == "merged" and result.previous_entry:
        restore_skill(
            result.previous_entry,
            db_path,
        )


def reject_skill_candidate(
    canonical_name: str,
    skill_type: str = DEFAULT_SKILL_TYPE,
    aliases: list[str] | None = None,
    db_path: str | Path | None = None,
) -> SkillRegistrySaveResult:
    return save_skill(
        canonical_name=canonical_name,
        skill_type=skill_type,
        aliases=aliases,
        source="human_review",
        status="rejected",
        db_path=db_path,
    )


def list_skills(
    status: str | None = "active",
    db_path: str | Path | None = None,
) -> list[SkillRegistryEntry]:
    path = initialize_skill_registry(
        db_path
    )
    params = []
    where = ""

    if status:
        where = "WHERE status = ?"
        params.append(status)

    with get_connection(path) as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM skill_registry
            {where}
            ORDER BY canonical_name
            """,
            params,
        ).fetchall()

        return [
            entry
            for entry in (
                _row_to_entry(connection, row)
                for row in rows
            )
            if entry is not None
        ]


def registry_alias_map(
    db_path: str | Path | None = None,
) -> dict[str, str]:
    if db_path is None:
        path = get_companyhub_db_path()
        if not path.exists():
            return {}
    else:
        path = initialize_skill_registry(
            db_path
        )

    with get_connection(path) as connection:
        rows = connection.execute(
            """
            SELECT sr.canonical_name, sr.canonical_key, alias.normalized_alias
            FROM skill_registry sr
            LEFT JOIN skill_registry_aliases alias
                ON alias.skill_id = sr.id
            WHERE sr.status IN ('active')
            """
        ).fetchall()

    aliases = {}

    for row in rows:
        aliases[row["canonical_key"]] = row["canonical_name"]
        if row["normalized_alias"]:
            aliases[row["normalized_alias"]] = row["canonical_name"]

    return aliases


def migrate_taxonomy_to_skill_registry(
    db_path: str | Path | None = None,
) -> dict[str, int]:
    path = initialize_skill_registry(
        db_path
    )
    snapshot = _snapshot_registry(
        path
    )

    try:
        import yaml

        taxonomy = yaml.safe_load(
            SKILL_TAXONOMY_FILE.read_text(
                encoding="utf-8",
            )
        ) or {}
    except Exception:
        taxonomy = {}

    created = 0
    merged = 0
    conflicts = 0

    try:
        for tag, data in taxonomy.items():
            data = data if isinstance(data, dict) else {}
            label = str(
                data.get("label") or tag
            )
            aliases = [
                tag,
                label,
            ]
            result = save_skill(
                canonical_name=tag,
                display_name=label,
                skill_type=DEFAULT_SKILL_TYPE,
                aliases=aliases,
                created_by="migration",
                source="skill_taxonomy.yaml",
                db_path=path,
            )
            if result.action == "created":
                created += 1
            elif result.action == "merged":
                merged += 1
            elif result.action == "conflict":
                conflicts += 1

        alias_groups = YamlTaxonomyRepository().load_aliases()

        for canonical_name, alias_values in alias_groups.items():
            canonical_alias_key = normalize_skill_registry_key(
                canonical_name
            )
            with get_connection(path) as connection:
                rows = connection.execute(
                    """
                    SELECT alias.id, alias.skill_id, sr.canonical_name,
                        sr.created_by, sr.source
                    FROM skill_registry_aliases alias
                    JOIN skill_registry sr
                        ON sr.id = alias.skill_id
                    WHERE alias.normalized_alias = ?
                        AND alias.type = ?
                        AND sr.canonical_name != ?
                    """,
                    (
                        canonical_alias_key,
                        DEFAULT_SKILL_TYPE,
                        canonical_name,
                    ),
                ).fetchall()
                for row in rows:
                    if (
                        row["created_by"] == "migration"
                        or str(row["source"]).endswith(".yaml")
                    ):
                        connection.execute(
                            """
                            DELETE FROM skill_registry_aliases
                            WHERE id = ?
                            """,
                            (
                                row["id"],
                            ),
                        )
                connection.commit()

            result = save_skill(
                canonical_name=canonical_name,
                skill_type=DEFAULT_SKILL_TYPE,
                aliases=[
                    canonical_name,
                ],
                created_by="migration",
                source="taxonomy_aliases.yaml",
                db_path=path,
            )
            if result.action == "created":
                created += 1
            elif result.action == "merged":
                merged += 1
            elif result.action == "conflict":
                conflicts += 1
                continue

            entry = result.entry
            if not entry or entry.id is None:
                continue

            with get_connection(path) as connection:
                for alias in alias_values:
                    normalized_alias = normalize_skill_registry_key(
                        alias
                    )
                    existing_alias = connection.execute(
                        """
                        SELECT alias.id, alias.skill_id, sr.created_by, sr.source
                        FROM skill_registry_aliases alias
                        JOIN skill_registry sr
                            ON sr.id = alias.skill_id
                        WHERE alias.normalized_alias = ?
                            AND alias.type = ?
                        """,
                        (
                            normalized_alias,
                            DEFAULT_SKILL_TYPE,
                        ),
                    ).fetchone()
                    if (
                        existing_alias
                        and existing_alias["skill_id"] != entry.id
                        and (
                            existing_alias["created_by"] == "migration"
                            or str(existing_alias["source"]).endswith(".yaml")
                        )
                    ):
                        connection.execute(
                            """
                            DELETE FROM skill_registry_aliases
                            WHERE id = ?
                            """,
                            (
                                existing_alias["id"],
                            ),
                        )
                    _insert_alias(
                        connection,
                        entry.id,
                        alias,
                        DEFAULT_SKILL_TYPE,
                    )
                connection.commit()
    except Exception:
        _restore_registry_snapshot(
            path,
            snapshot,
        )
        raise

    return {
        "created": created,
        "merged": merged,
        "conflicts": conflicts,
    }


def persist_reviewed_skill(
    review_item: dict,
    status: str = "approved",
    canonical_name: str | None = None,
    skill_type: str | None = None,
    aliases: list[str] | None = None,
    existing_skill_id: int | None = None,
    db_path: str | Path | None = None,
) -> SkillRegistrySaveResult:
    candidate_name = _display_name(
        review_item.get("name")
        or review_item.get("canonical_name")
        or review_item.get("suggested_tag")
        or ""
    )
    canonical = _display_name(
        canonical_name
        or review_item.get("canonical_name")
        or candidate_name
    )
    candidate_type = _type_value(
        skill_type
        or review_item.get("candidate_type")
        or DEFAULT_SKILL_TYPE
    )
    alias_values = [
        candidate_name,
        str(review_item.get("suggested_tag") or ""),
        str(review_item.get("canonical_name") or ""),
    ]
    alias_values.extend(
        aliases or []
    )

    if status == "rejected":
        return SkillRegistrySaveResult(
            entry=None,
            action="rejected",
        )

    if existing_skill_id:
        existing = get_skill_by_id(
            existing_skill_id,
            db_path,
        )
        if existing is None:
            raise ValueError(
                f"Unknown skill id: {existing_skill_id}"
            )
        canonical = existing.canonical_name
        candidate_type = existing.type

    return save_skill(
        canonical_name=canonical,
        skill_type=candidate_type,
        aliases=alias_values,
        display_name=canonical,
        created_by="human_review",
        source="review_queue",
        status="active",
        db_path=db_path,
    )
