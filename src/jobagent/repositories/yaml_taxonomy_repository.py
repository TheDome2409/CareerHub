from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TAXONOMY_DIR = PROJECT_ROOT / "config" / "taxonomy"


class YamlTaxonomyRepository:
    def __init__(self, taxonomy_dir: str | Path | None = None):
        self.taxonomy_dir = Path(
            taxonomy_dir or DEFAULT_TAXONOMY_DIR
        )

    def _load_yaml_dict(self, filename: str) -> dict:
        path = self.taxonomy_dir / filename

        if not path.exists():
            return {}

        try:
            raw_content = path.read_text(
                encoding="utf-8",
            ).strip()
        except OSError:
            return {}

        if not raw_content:
            return {}

        try:
            data = yaml.safe_load(
                raw_content
            )
        except yaml.YAMLError:
            return {}

        if not isinstance(data, dict):
            return {}

        return data

    def load_aliases(self) -> dict[str, set[str]]:
        data = self._load_yaml_dict(
            "aliases.yaml"
        )
        aliases = data.get(
            "aliases",
            data,
        )

        if not isinstance(aliases, dict):
            return {}

        return {
            str(canonical): {
                str(alias)
                for alias in values or []
                if str(alias).strip()
            }
            for canonical, values in aliases.items()
            if isinstance(values, list)
        }

    def load_competencies(self) -> dict:
        return self._load_yaml_dict(
            "competencies.yaml"
        )

    def load_qualifications(self) -> dict:
        return self._load_yaml_dict(
            "qualifications.yaml"
        )

    def load_job_intelligence_patterns(self) -> dict:
        return self._load_yaml_dict(
            "job_intelligence.yaml"
        )
