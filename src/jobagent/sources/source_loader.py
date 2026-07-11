from pathlib import Path

import yaml

from jobagent.sources.source_config import SourcesConfig


def load_sources(path: str | Path) -> SourcesConfig:
    with open(path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if data is None:
        raise ValueError(f"Sources config is empty: {path}")

    return SourcesConfig.model_validate(data)