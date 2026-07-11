import json
from pathlib import Path

from jobagent.models.company import CompanyProfile


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_COMPANY_PROFILE_DIR = PROJECT_ROOT / "data" / "company_profiles"
SUPPORTED_SUFFIXES = {
    ".json",
    ".yaml",
    ".yml",
}


def _load_raw_profile(path: Path) -> dict:
    if path.suffix.lower() == ".json":
        return json.loads(
            path.read_text(encoding="utf-8")
        )

    try:
        import yaml
    except ImportError:
        return {}

    loaded = yaml.safe_load(
        path.read_text(encoding="utf-8")
    )

    return loaded if isinstance(loaded, dict) else {}


def load_company_profile(path: str | Path) -> CompanyProfile | None:
    path = Path(path)

    if not path.exists() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
        return None

    raw = _load_raw_profile(
        path
    )

    if not raw:
        return None

    return CompanyProfile.model_validate(
        raw
    )


def load_company_profiles(
    path: str | Path = DEFAULT_COMPANY_PROFILE_DIR,
) -> list[CompanyProfile]:
    path = Path(path)

    if not path.exists():
        return []

    if path.is_file():
        profile = load_company_profile(
            path
        )
        return [profile] if profile else []

    profiles = []

    for profile_path in sorted(path.iterdir()):
        if profile_path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue

        profile = load_company_profile(
            profile_path
        )

        if profile:
            profiles.append(
                profile
            )

    return profiles
