from jobagent.services.company_matching_config_service import (
    DEFAULT_COMPANY_MATCHING_CONFIG,
    load_company_matching_config,
)


def test_company_matching_config_uses_defaults_for_missing_file(tmp_path):
    config = load_company_matching_config(
        tmp_path / "missing.yaml"
    )

    assert config == DEFAULT_COMPANY_MATCHING_CONFIG
    assert config.mission_weight == 25
    assert config.neutral_score_without_profile == 50
    assert config.missing_work_model_penalty == 0


def test_company_matching_config_uses_defaults_for_invalid_values(tmp_path):
    tmp_path.mkdir(
        parents=True,
        exist_ok=True,
    )
    config_path = tmp_path / "company_matching.yaml"
    config_path.write_text(
        "mission_weight: nope\nwork_model_weight: 20\n",
        encoding="utf-8",
    )

    config = load_company_matching_config(
        config_path
    )

    assert config.mission_weight == 25
    assert config.work_model_weight == 20


def test_company_matching_config_loads_yaml_values(tmp_path):
    tmp_path.mkdir(
        parents=True,
        exist_ok=True,
    )
    config_path = tmp_path / "company_matching.yaml"
    config_path.write_text(
        "\n".join(
            [
                "mission_weight: 30",
                "domain_weight: 20",
                "technology_weight: 12",
                "work_model_weight: 18",
                "kritis_weight: 9",
                "max_exclusion_penalty: 25",
                "neutral_score_without_profile: 45",
                "missing_work_model_penalty: 3",
            ]
        ),
        encoding="utf-8",
    )

    config = load_company_matching_config(
        config_path
    )

    assert config.mission_weight == 30
    assert config.domain_weight == 20
    assert config.technology_weight == 12
    assert config.work_model_weight == 18
    assert config.kritis_weight == 9
    assert config.max_exclusion_penalty == 25
    assert config.neutral_score_without_profile == 45
    assert config.missing_work_model_penalty == 3
