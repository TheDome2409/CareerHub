from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_COMPANY_MATCHING_CONFIG_PATH = (
    PROJECT_ROOT / "config" / "company_matching" / "company_matching.yaml"
)


@dataclass(frozen=True)
class CompanyMatchingConfig:
    mission_weight: int = 25
    domain_weight: int = 25
    technology_weight: int = 15
    work_model_weight: int = 15
    kritis_weight: int = 10
    max_exclusion_penalty: int = 30
    neutral_score_without_profile: int = 50
    missing_work_model_penalty: int = 0


DEFAULT_COMPANY_MATCHING_CONFIG = CompanyMatchingConfig()


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}

    text = path.read_text(
        encoding="utf-8"
    )

    try:
        import yaml
    except ImportError:
        return _load_flat_yaml(text)

    try:
        loaded = yaml.safe_load(
            text
        )
    except Exception:
        return {}

    return loaded if isinstance(loaded, dict) else {}


def _load_flat_yaml(text: str) -> dict:
    data = {}

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue

        key, value = stripped.split(
            ":",
            1,
        )
        key = key.strip()
        value = value.strip().strip("\"'")

        if key:
            data[key] = value

    return data


def _int_value(data: dict, key: str, default: int) -> int:
    try:
        return int(
            data.get(key, default)
        )
    except (TypeError, ValueError):
        return default


def load_company_matching_config(
    path: str | Path | None = None,
) -> CompanyMatchingConfig:
    config_path = Path(
        path or DEFAULT_COMPANY_MATCHING_CONFIG_PATH
    )
    data = _load_yaml(
        config_path
    )
    defaults = DEFAULT_COMPANY_MATCHING_CONFIG

    return CompanyMatchingConfig(
        mission_weight=_int_value(
            data,
            "mission_weight",
            defaults.mission_weight,
        ),
        domain_weight=_int_value(
            data,
            "domain_weight",
            defaults.domain_weight,
        ),
        technology_weight=_int_value(
            data,
            "technology_weight",
            defaults.technology_weight,
        ),
        work_model_weight=_int_value(
            data,
            "work_model_weight",
            defaults.work_model_weight,
        ),
        kritis_weight=_int_value(
            data,
            "kritis_weight",
            defaults.kritis_weight,
        ),
        max_exclusion_penalty=_int_value(
            data,
            "max_exclusion_penalty",
            defaults.max_exclusion_penalty,
        ),
        neutral_score_without_profile=_int_value(
            data,
            "neutral_score_without_profile",
            defaults.neutral_score_without_profile,
        ),
        missing_work_model_penalty=_int_value(
            data,
            "missing_work_model_penalty",
            defaults.missing_work_model_penalty,
        ),
    )
