from collections import Counter
from pathlib import Path

from jobagent.models.company import (
    CompanyGroundTruthReview,
    CompanyGroundTruthTopic,
    CompanyGroundTruthUserAssessment,
)
from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.companyhub_db_service import (
    get_connection,
    initialize_companyhub_db,
)


GROUND_TRUTH_TOPICS: tuple[str, ...] = (
    "culture",
    "leadership",
    "innovation",
    "digitalization",
    "work_life_balance",
    "process_quality",
    "technology",
    "career",
    "stability",
    "sustainability",
    "employer_branding",
    "other",
)

USER_ASSESSMENTS: tuple[str, ...] = (
    "stimmt",
    "teilweise",
    "falsch",
    "unbekannt",
)

ASSESSMENT_SCORES = {
    "stimmt": 1.0,
    "teilweise": 0.5,
    "falsch": 0.0,
}


def _ensure_schema(db_path: str | Path | None = None) -> Path:
    path = initialize_companyhub_db(
        Path(db_path) if db_path else None
    )

    with get_connection(path) as connection:
        connection.execute(
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
            """
        )
        connection.commit()

    return path


def _review_from_row(row) -> CompanyGroundTruthReview | None:
    if row is None:
        return None

    return CompanyGroundTruthReview(
        company_id=row["company_id"],
        topic=row["topic"],
        claim=row["claim"],
        system_assessment=row["system_assessment"],
        user_assessment=row["user_assessment"],
        user_comment=row["user_comment"],
        confidence=float(row["confidence"] or 0),
        created_at=row["created_at"],
    )


def add_ground_truth_review(
    company_id: int | str,
    topic: CompanyGroundTruthTopic,
    claim: str,
    system_assessment: str,
    user_assessment: CompanyGroundTruthUserAssessment,
    user_comment: str = "",
    confidence: float = 0.0,
    db_path: str | Path | None = None,
) -> CompanyGroundTruthReview:
    review = CompanyGroundTruthReview(
        company_id=str(company_id),
        topic=topic,
        claim=claim,
        system_assessment=system_assessment,
        user_assessment=user_assessment,
        user_comment=user_comment,
        confidence=max(
            0.0,
            min(
                1.0,
                float(confidence or 0),
            ),
        ),
    )
    path = _ensure_schema(
        db_path
    )

    with get_connection(path) as connection:
        connection.execute(
            """
            INSERT INTO company_ground_truth_reviews (
                company_id,
                topic,
                claim,
                system_assessment,
                user_assessment,
                user_comment,
                confidence,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(review.company_id),
                review.topic,
                review.claim,
                review.system_assessment,
                review.user_assessment,
                review.user_comment,
                review.confidence,
                review.created_at,
            ),
        )
        connection.commit()

    return review


def list_ground_truth_reviews(
    company_id: int | str,
    db_path: str | Path | None = None,
) -> list[CompanyGroundTruthReview]:
    path = _ensure_schema(
        db_path
    )

    with get_connection(path) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM company_ground_truth_reviews
            WHERE company_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (str(company_id),),
        ).fetchall()

    return [
        review
        for review in (
            _review_from_row(row)
            for row in rows
        )
        if review is not None
    ]


def compare_system_assessment_with_user_review(
    system_assessment: str,
    user_assessment: str,
) -> str:
    del system_assessment

    if user_assessment == "stimmt":
        return "match"
    if user_assessment == "teilweise":
        return "partial"
    if user_assessment == "falsch":
        return "mismatch"

    return "unknown"


def calculate_ground_truth_accuracy(
    company_id: int | str,
    db_path: str | Path | None = None,
) -> dict:
    reviews = list_ground_truth_reviews(
        company_id,
        db_path=db_path,
    )
    counts = Counter(
        review.user_assessment
        for review in reviews
    )
    rated_reviews = [
        review
        for review in reviews
        if review.user_assessment in ASSESSMENT_SCORES
    ]
    score_sum = sum(
        ASSESSMENT_SCORES[review.user_assessment]
        for review in rated_reviews
    )
    accuracy = (
        score_sum / len(rated_reviews)
        if rated_reviews
        else None
    )

    return {
        "company_id": str(company_id),
        "total_reviews": len(reviews),
        "rated_reviews": len(rated_reviews),
        "unknown_count": counts.get("unbekannt", 0),
        "counts": {
            assessment: counts.get(assessment, 0)
            for assessment in USER_ASSESSMENTS
        },
        "accuracy": accuracy,
    }


def mark_company_as_ground_truth(
    company_id: int,
    relationship_status: str | None = None,
    repository: CompanyRepository | None = None,
):
    return (repository or CompanyRepository()).mark_company_ground_truth_available(
        company_id=company_id,
        relationship_status=relationship_status,
    )


def ensure_xox_ground_truth_company(
    repository: CompanyRepository | None = None,
):
    repo = repository or CompanyRepository()
    company = repo.upsert_company(
        name="Example Foods",
        industry="food",
        ground_truth_available=True,
        relationship_status="former_employer",
    )

    return company
