from types import SimpleNamespace

from jobagent.models.company_knowledge_draft import CompanyKnowledgeDraft
from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.company_profile_match_service import (
    match_all_tracked_companies,
    match_company_to_profile,
)
from jobagent.services.company_recommendation_service import track_recommended_company
from jobagent.models.recommended_company import RecommendedCompany


def _company_with_draft(repository: CompanyRepository, draft: CompanyKnowledgeDraft):
    company = repository.upsert_company("DB InfraGO")
    draft.company_id = company.id
    repository.save_company_knowledge_draft(draft)

    return company


def _profile(
    skills=None,
    interests=None,
    preferred_roles=None,
    work_preferred=None,
    work_acceptable=None,
    exclusions=None,
):
    return SimpleNamespace(
        skills=skills or [],
        certifications=[],
        preferred_roles=preferred_roles or [],
        interests=interests or [],
        career_goals=SimpleNamespace(
            short_term=[],
            mid_term=[],
            long_term=[],
        ),
        employer_preferences=SimpleNamespace(
            positive=[],
        ),
        work_model=SimpleNamespace(
            preferred=work_preferred or [],
            acceptable=work_acceptable or [],
        ),
        exclusions=SimpleNamespace(
            industries=(exclusions or {}).get("industries", []),
            employment_models=(exclusions or {}).get("employment_models", []),
            requirements=(exclusions or {}).get("requirements", []),
        ),
    )


def test_profile_match_scores_kritis_and_infrastructure(tmp_path):
    repository = CompanyRepository(tmp_path / "companyhub.db")
    company = _company_with_draft(
        repository,
        CompanyKnowledgeDraft(
            company_id=0,
            business_domains=["Rail Infrastructure"],
            canonical_concepts=["infrastructure:Rail Infrastructure"],
            kritis_relevance=True,
            concept_statistics={
                "canonical": 2,
            },
        ),
    )
    profile = _profile(
        interests=["Infrastruktur", "KRITIS"],
    )

    match = match_company_to_profile(
        company.id,
        profile=profile,
        profile_fingerprint="profile-1",
        repository=repository,
    )

    assert match.kritis_score == 10
    assert match.domain_score > 0
    assert match.total_score > 0
    assert any("kritischer Infrastruktur" in reason for reason in match.reasons)


def test_profile_match_without_profile_is_neutral_low_confidence(tmp_path):
    repository = CompanyRepository(tmp_path / "companyhub.db")
    company = _company_with_draft(
        repository,
        CompanyKnowledgeDraft(
            company_id=0,
            technologies=["Azure"],
            concept_statistics={
                "canonical": 1,
            },
        ),
    )

    match = match_company_to_profile(
        company.id,
        profile=None,
        profile_fingerprint="default",
        repository=repository,
    )

    assert match.total_score == 50
    assert match.confidence == 0.2
    assert "profile_terms" in match.missing_profile_preferences


def test_exclusion_lowers_score_and_creates_risk(tmp_path):
    repository = CompanyRepository(tmp_path / "companyhub.db")
    company = _company_with_draft(
        repository,
        CompanyKnowledgeDraft(
            company_id=0,
            industries=["Banking"],
            canonical_concepts=["industry:Banking"],
            concept_statistics={
                "canonical": 1,
            },
        ),
    )
    profile = _profile(
        interests=["Banking"],
        exclusions={
            "industries": ["banking"],
        },
    )

    match = match_company_to_profile(
        company.id,
        profile=profile,
        profile_fingerprint="profile-1",
        repository=repository,
    )

    assert match.exclusion_score < 0
    assert match.risk_flags
    assert match.total_score < 25


def test_work_model_and_domain_match(tmp_path):
    repository = CompanyRepository(tmp_path / "companyhub.db")
    company = _company_with_draft(
        repository,
        CompanyKnowledgeDraft(
            company_id=0,
            business_domains=["Agricultural Digitalization"],
            work_models=["Hybrid"],
            canonical_concepts=[
                "company_domain:Agricultural Digitalization",
                "work_model:Hybrid",
            ],
            concept_statistics={
                "canonical": 2,
            },
        ),
    )
    profile = _profile(
        interests=["Digitalisierung"],
        work_preferred=["hybrid"],
    )

    match = match_company_to_profile(
        company.id,
        profile=profile,
        profile_fingerprint="profile-1",
        repository=repository,
    )

    assert match.domain_score > 0
    assert match.work_model_score == 15
    assert "hybrid" in match.matched_concepts


def test_profile_match_persistence_roundtrip(tmp_path):
    repository = CompanyRepository(tmp_path / "companyhub.db")
    company = _company_with_draft(
        repository,
        CompanyKnowledgeDraft(
            company_id=0,
            mission_keywords=["Digital Transformation"],
            concept_statistics={
                "canonical": 1,
            },
        ),
    )

    saved = match_company_to_profile(
        company.id,
        profile=_profile(interests=["Digital Transformation"]),
        profile_fingerprint="profile-1",
        repository=repository,
    )
    latest = repository.load_latest_company_profile_match(
        company.id,
        "profile-1",
    )
    matches = repository.list_company_profile_matches(
        "profile-1"
    )

    assert latest.total_score == saved.total_score
    assert latest.reasons
    assert len(matches) == 1


def test_company_match_uses_profile_mission_keywords(tmp_path):
    repository = CompanyRepository(tmp_path / "companyhub.db")
    company = _company_with_draft(
        repository,
        CompanyKnowledgeDraft(
            company_id=0,
            mission_keywords=["Digital Workplace"],
            technologies=["Azure"],
            concept_statistics={
                "canonical": 2,
            },
        ),
    )
    profile = _profile(
        skills=[
            "Microsoft 365",
        ],
    )

    match = match_company_to_profile(
        company.id,
        profile=profile,
        profile_fingerprint="profile-1",
        repository=repository,
    )

    assert match.mission_score == 25
    assert "digital workplace" in match.matched_concepts


def test_match_all_tracked_companies(tmp_path):
    repository = CompanyRepository(tmp_path / "companyhub.db")
    company = _company_with_draft(
        repository,
        CompanyKnowledgeDraft(
            company_id=0,
            technologies=["Azure"],
            concept_statistics={
                "canonical": 1,
            },
        ),
    )
    track_recommended_company(
        RecommendedCompany(
            company_id=company.id,
            name=company.name,
            priority=1,
            reason="Test",
            recommended_by="test",
            tags=["technology"],
        ),
        "profile-1",
        repository=repository,
    )

    matches = match_all_tracked_companies(
        profile=_profile(skills=["Azure"]),
        profile_fingerprint="profile-1",
        repository=repository,
    )

    assert len(matches) == 1
    assert matches[0].technology_score == 15
