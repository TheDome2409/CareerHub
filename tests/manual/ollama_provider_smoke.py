r"""Manual Ollama provider smoke test.

This script is intentionally not named ``test_*.py`` so pytest does not collect
it during normal unit-test runs. It requires a running local Ollama server and a
configured model.

Usage:

    python tests\manual\ollama_provider_smoke.py
"""

from __future__ import annotations

from jobagent.services.ollama_provider import OllamaProvider


def main() -> int:
    provider = OllamaProvider()

    text = """
    Beratung der Geschäftsführung bei technischen Entscheidungsprozessen.
    Koordination interner und externer Teams.
    Dienstleistersteuerung.
    """

    for skill in provider.extract_skills(text):
        print(skill)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
