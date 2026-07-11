from jobagent.models.recommended_company import RecommendedCompany
from jobagent.services.company_recommendation_service import (
    get_recommended_companies,
)


def test_recommended_companies_are_not_empty():
    companies = get_recommended_companies()

    assert companies
    assert all(
        isinstance(company, RecommendedCompany)
        for company in companies
    )


def test_recommended_companies_include_required_seed_companies():
    names = {
        company.name
        for company in get_recommended_companies()
    }

    assert "Dataport" in names
    assert "KWS" in names
    assert "DB InfraGO" in names
    assert "Amprion" in names
    assert "Avacon" in names
    assert "Westfalen Weser" in names
    assert "Deutsche Telekom" in names


def test_recommended_companies_are_sorted_by_priority():
    priorities = [
        company.priority
        for company in get_recommended_companies()
    ]

    assert priorities == sorted(
        priorities
    )
    assert get_recommended_companies()[0].priority == 1


def test_recommended_companies_have_tags_and_reasons():
    companies = get_recommended_companies()

    assert all(
        company.reason
        for company in companies
    )
    assert all(
        company.tags
        for company in companies
    )

    dataport = next(
        company
        for company in companies
        if company.name == "Dataport"
    )
    assert "public_sector" in dataport.tags
    assert "digitalization" in dataport.tags
    assert dataport.recommended_by == "seed"
    assert dataport.tracking_enabled is True


def test_recommended_companies_have_no_duplicate_names():
    names = [
        company.name.lower()
        for company in get_recommended_companies()
    ]

    assert len(names) == len(
        set(names)
    )


def test_recommended_companies_accept_profile_argument_without_changing_api():
    companies = get_recommended_companies(
        profile={
            "skills": [
                "digitalization",
            ]
        }
    )

    assert companies
