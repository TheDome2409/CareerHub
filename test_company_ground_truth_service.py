from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.company_ground_truth_service import (
    add_ground_truth_review,
    calculate_ground_truth_accuracy,
    compare_system_assessment_with_user_review,
    ensure_xox_ground_truth_company,
    list_ground_truth_reviews,
)
from jobagent.services.company_profile_loader import load_company_profile


def test_ground_truth_review_roundtrip(tmp_path):
    db_path = tmp_path / "companyhub.db"

    saved = add_ground_truth_review(
        company_id=1,
        topic="digitalization",
        claim="Unternehmen wirkt digital fortgeschritten.",
        system_assessment="digital fortgeschritten",
        user_assessment="teilweise",
        user_comment="Produktion ja, interne IT-Prozesse nein.",
        confidence=0.8,
        db_path=db_path,
    )

    reviews = list_ground_truth_reviews(
        1,
        db_path=db_path,
    )

    assert len(reviews) == 1
    assert reviews[0] == saved
    assert reviews[0].topic == "digitalization"
    assert reviews[0].user_assessment == "teilweise"


def test_ground_truth_accuracy_counts_reviews(tmp_path):
    db_path = tmp_path / "companyhub.db"

    add_ground_truth_review(
        7,
        "culture",
        "Kultur ist offen.",
        "offen",
        "stimmt",
        db_path=db_path,
    )
    add_ground_truth_review(
        7,
        "technology",
        "Technologie ist modern.",
        "modern",
        "teilweise",
        db_path=db_path,
    )
    add_ground_truth_review(
        7,
        "leadership",
        "Fuehrung ist transparent.",
        "transparent",
        "falsch",
        db_path=db_path,
    )
    add_ground_truth_review(
        7,
        "stability",
        "Stabilitaet ist hoch.",
        "hoch",
        "unbekannt",
        db_path=db_path,
    )

    summary = calculate_ground_truth_accuracy(
        7,
        db_path=db_path,
    )

    assert summary["total_reviews"] == 4
    assert summary["rated_reviews"] == 3
    assert summary["unknown_count"] == 1
    assert summary["counts"]["stimmt"] == 1
    assert summary["counts"]["teilweise"] == 1
    assert summary["counts"]["falsch"] == 1
    assert summary["accuracy"] == 0.5


def test_compare_system_assessment_with_user_review():
    assert (
        compare_system_assessment_with_user_review("digital", "stimmt")
        == "match"
    )
    assert (
        compare_system_assessment_with_user_review("digital", "teilweise")
        == "partial"
    )
    assert (
        compare_system_assessment_with_user_review("digital", "falsch")
        == "mismatch"
    )
    assert (
        compare_system_assessment_with_user_review("digital", "unbekannt")
        == "unknown"
    )


def test_xox_ground_truth_company_can_be_created(tmp_path):
    repository = CompanyRepository(
        tmp_path / "companyhub.db"
    )

    company = ensure_xox_ground_truth_company(
        repository=repository
    )
    loaded = repository.get_company_by_id(
        company.id
    )

    assert loaded.name == "Example Foods"
    assert loaded.ground_truth_available is True
    assert loaded.relationship_status == "former_employer"


def test_xox_manual_profile_is_ground_truth_available():
    profile = load_company_profile(
        "data/company_profiles/xox.json"
    )

    assert profile.name == "Example Foods"
    assert profile.ground_truth_available is True
    assert profile.relationship_status == "former_employer"
