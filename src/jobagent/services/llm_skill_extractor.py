import json

from jobagent.models.skill_candidate import (
    SkillCandidate,
)


def parse_llm_skill_response(
    response_text: str,
) -> list[SkillCandidate]:
    try:
        data = json.loads(response_text)

    except Exception:
        return []

    skills = []

    for item in data:
        try:
            skills.append(
                SkillCandidate(
                    name=item["skill"],
                    category=item["skill"],
                    confidence=float(
                        item.get(
                            "confidence",
                            0.5,
                        )
                    ),
                    source=item.get(
                        "evidence",
                        "",
                    ),
                    provider="llm",
                    weight=5,
                    enabled=False,
                )
            )

        except Exception:
            continue

    return skills


def extract_skills_with_llm(
    text: str,
) -> list[SkillCandidate]:
    """
    Platzhalter für zukünftige LLM-Analyse.

    Aktuell liefert die Funktion keine Skills zurück.
    """

    return []
