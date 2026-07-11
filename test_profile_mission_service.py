from types import SimpleNamespace

from jobagent.services.profile_mission_service import (
    build_profile_mission,
    load_profile_mission,
)


def _profile(
    skills=None,
    interests=None,
    preferred_roles=None,
    work_preferred=None,
    work_acceptable=None,
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
    )


def test_build_profile_mission_abstacts_digital_workplace_and_business_digitalization():
    mission = build_profile_mission(
        _profile(
            skills=[
                "Azure",
                "Microsoft 365",
                "EDI",
                "SAP",
            ],
            interests=[
                "Digitalisierung",
            ],
            work_preferred=[
                "hybrid",
            ],
        )
    )

    assert "Digital Workplace" in mission.mission_keywords
    assert "Business Digitalization" in mission.mission_keywords
    assert "Azure" in mission.preferred_technologies
    assert "SAP / ERP" in mission.preferred_technologies
    assert mission.preferred_work_models == [
        "hybrid",
    ]
    assert mission.confidence > 0.5


def test_build_profile_mission_detects_kritis_public_research_and_innovation():
    mission = build_profile_mission(
        _profile(
            skills=[
                "KRITIS",
                "Bahn",
                "Prototyping",
            ],
            interests=[
                "Public Sector",
                "Research",
            ],
        )
    )

    assert "Critical Infrastructure" in mission.mission_keywords
    assert "Product Innovation" in mission.mission_keywords
    assert mission.kritis_affinity == 1.0
    assert mission.innovation_affinity == 1.0
    assert mission.public_sector_affinity == 1.0
    assert mission.research_affinity == 1.0
    assert "robuster, sicherer und effizienter" in mission.summary


def test_build_profile_mission_without_profile_is_low_confidence():
    mission = build_profile_mission(None)

    assert mission.confidence == 0.2
    assert mission.mission_keywords == []
    assert mission.summary


def test_load_profile_mission_accepts_explicit_profile():
    mission = load_profile_mission(
        _profile(
            skills=[
                "ERP",
            ],
        )
    )

    assert "Business Digitalization" in mission.mission_keywords
