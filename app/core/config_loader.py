from pathlib import Path
import yaml

from app.models.profile import ProfileConfig
from app.models.scoring import ScoringConfig


def load_yaml(path: str | Path) -> dict:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_profile(path: str | Path) -> ProfileConfig:
    data = load_yaml(path)
    return ProfileConfig.model_validate(data)


def load_scoring(path: str | Path) -> ScoringConfig:
    data = load_yaml(path)
    return ScoringConfig.model_validate(data)