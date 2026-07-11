from pathlib import Path

from jobagent.repositories import YamlTaxonomyRepository


def test_yaml_taxonomy_repository_loads_taxonomy_files():
    repository = YamlTaxonomyRepository()

    aliases = repository.load_aliases()
    competencies = repository.load_competencies()
    qualifications = repository.load_qualifications()
    job_intelligence = repository.load_job_intelligence_patterns()

    assert "artificial_intelligence" in aliases
    assert "skill_competency_mapping" in competencies
    assert "qualification_rules" in qualifications
    assert "skill_patterns" in job_intelligence


def test_yaml_taxonomy_repository_tolerates_missing_empty_invalid_files(
    tmp_path: Path,
):
    repository = YamlTaxonomyRepository(
        tmp_path
    )

    assert repository.load_aliases() == {}
    assert repository.load_competencies() == {}

    (tmp_path / "aliases.yaml").write_text(
        "",
        encoding="utf-8",
    )
    assert repository.load_aliases() == {}

    (tmp_path / "aliases.yaml").write_text(
        "[",
        encoding="utf-8",
    )
    assert repository.load_aliases() == {}
