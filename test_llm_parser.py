from jobagent.services.llm_skill_extractor import (
    parse_llm_skill_response,
)

response = """
[
  {
    "skill": "consulting",
    "confidence": 0.9,
    "evidence": "Beratung der Geschäftsführung"
  },
  {
    "skill": "stakeholder_management",
    "confidence": 0.8,
    "evidence": "Koordination interner und externer Teams"
  }
]
"""

skills = parse_llm_skill_response(
    response
)

for skill in skills:
    print(skill)