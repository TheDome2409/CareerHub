from pathlib import Path


def test_profile_tab_contains_mission_profile_ui():
    source = Path(
        "src/jobagent/ui/profile_tab.py"
    ).read_text(
        encoding="utf-8"
    )

    assert "Mission Profil" in source
    assert "build_profile_mission" in source
    assert "Mission Summary" in source
    assert "Mission Keywords" in source
    assert "KRITIS Affinity" in source
