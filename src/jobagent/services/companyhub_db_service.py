import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_COMPANYHUB_DB_PATH = PROJECT_ROOT / "data" / "companyhub.db"


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        normalized_name TEXT NOT NULL UNIQUE,
        website_url TEXT,
        career_url TEXT,
        industry TEXT,
        status TEXT DEFAULT 'active',
        ground_truth_available INTEGER DEFAULT 0,
        relationship_status TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS company_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        mission TEXT,
        vision TEXT,
        culture_summary TEXT,
        technology_summary TEXT,
        domains_json TEXT,
        work_models_json TEXT,
        locations_json TEXT,
        kritis_relevance INTEGER DEFAULT 0,
        innovation_score INTEGER,
        source_summary TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(company_id) REFERENCES companies(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tracked_companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        profile_fingerprint TEXT NOT NULL,
        priority INTEGER DEFAULT 3,
        notes TEXT,
        active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(company_id) REFERENCES companies(id),
        UNIQUE(company_id, profile_fingerprint)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS company_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        source_type TEXT NOT NULL,
        url TEXT,
        title TEXT,
        description TEXT,
        enabled INTEGER DEFAULT 1,
        priority INTEGER DEFAULT 3,
        last_checked TEXT,
        last_success TEXT,
        etag TEXT,
        content_hash TEXT,
        notes TEXT,
        created_at TEXT,
        fetched_at TEXT,
        perspective TEXT,
        raw_excerpt TEXT,
        FOREIGN KEY(company_id) REFERENCES companies(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS company_observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        source_id INTEGER,
        observation_type TEXT NOT NULL,
        value TEXT,
        confidence REAL,
        evidence_text TEXT,
        perspective TEXT,
        observed_at TEXT NOT NULL,
        FOREIGN KEY(company_id) REFERENCES companies(id),
        FOREIGN KEY(source_id) REFERENCES company_sources(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS company_match_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        profile_fingerprint TEXT NOT NULL,
        mission_score INTEGER,
        culture_score INTEGER,
        technology_score INTEGER,
        work_model_score INTEGER,
        travel_score INTEGER,
        total_score INTEGER,
        reasons_json TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(company_id) REFERENCES companies(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS company_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        source_id INTEGER NOT NULL,
        content_type TEXT,
        mime_type TEXT,
        charset TEXT,
        url TEXT,
        title TEXT,
        status_code INTEGER,
        content_hash TEXT,
        content_text TEXT,
        content_size INTEGER,
        fetched_at TEXT NOT NULL,
        last_modified_header TEXT,
        etag TEXT,
        request_duration_ms INTEGER,
        FOREIGN KEY(company_id) REFERENCES companies(id),
        FOREIGN KEY(source_id) REFERENCES company_sources(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS company_relationships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        related_company_id INTEGER,
        related_company_name TEXT NOT NULL,
        relationship_type TEXT NOT NULL,
        direction TEXT DEFAULT 'unknown',
        confidence REAL,
        source TEXT,
        source_url TEXT,
        evidence_text TEXT,
        active INTEGER DEFAULT 1,
        observed_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(company_id) REFERENCES companies(id),
        FOREIGN KEY(related_company_id) REFERENCES companies(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS company_evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        document_id INTEGER,
        evidence_type TEXT NOT NULL,
        title TEXT,
        text TEXT NOT NULL,
        source_type TEXT,
        source_name TEXT,
        source_url TEXT,
        section TEXT,
        confidence REAL,
        language TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(company_id) REFERENCES companies(id),
        FOREIGN KEY(document_id) REFERENCES company_documents(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS company_knowledge_drafts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        draft_json TEXT NOT NULL,
        confidence REAL,
        evidence_count INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY(company_id) REFERENCES companies(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS company_ground_truth_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL,
        topic TEXT NOT NULL,
        claim TEXT NOT NULL,
        system_assessment TEXT NOT NULL,
        user_assessment TEXT NOT NULL,
        user_comment TEXT NOT NULL DEFAULT '',
        confidence REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS skill_registry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        canonical_name TEXT NOT NULL,
        canonical_key TEXT NOT NULL,
        display_name TEXT NOT NULL,
        type TEXT NOT NULL DEFAULT 'skill',
        description TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT NOT NULL DEFAULT 'system',
        source TEXT NOT NULL DEFAULT 'unknown',
        status TEXT NOT NULL DEFAULT 'active',
        UNIQUE(canonical_key, type)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS skill_registry_aliases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        skill_id INTEGER NOT NULL,
        alias TEXT NOT NULL,
        normalized_alias TEXT NOT NULL,
        type TEXT NOT NULL DEFAULT 'skill',
        created_at TEXT NOT NULL,
        FOREIGN KEY(skill_id) REFERENCES skill_registry(id),
        UNIQUE(normalized_alias, type)
    )
    """,
]


MIGRATION_STATEMENTS = [
    "ALTER TABLE company_sources ADD COLUMN description TEXT",
    "ALTER TABLE company_sources ADD COLUMN enabled INTEGER DEFAULT 1",
    "ALTER TABLE company_sources ADD COLUMN priority INTEGER DEFAULT 3",
    "ALTER TABLE company_sources ADD COLUMN last_checked TEXT",
    "ALTER TABLE company_sources ADD COLUMN last_success TEXT",
    "ALTER TABLE company_sources ADD COLUMN etag TEXT",
    "ALTER TABLE company_sources ADD COLUMN notes TEXT",
    "ALTER TABLE company_sources ADD COLUMN created_at TEXT",
    "ALTER TABLE companies ADD COLUMN ground_truth_available INTEGER DEFAULT 0",
    "ALTER TABLE companies ADD COLUMN relationship_status TEXT",
]


def get_companyhub_db_path() -> Path:
    return DEFAULT_COMPANYHUB_DB_PATH


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or get_companyhub_db_path())
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    connection = sqlite3.connect(
        path
    )
    connection.row_factory = sqlite3.Row
    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


def initialize_companyhub_db(db_path: Path | None = None) -> Path:
    path = Path(db_path or get_companyhub_db_path())
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with get_connection(path) as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        for statement in MIGRATION_STATEMENTS:
            try:
                connection.execute(statement)
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise

    return path
