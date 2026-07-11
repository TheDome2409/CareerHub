from ollama import chat

from jobagent.services.llm_provider import LlmProvider
from jobagent.services.llm_skill_extractor import (
    parse_llm_skill_response,
)


class OllamaProvider(LlmProvider):
    def __init__(
        self,
        model: str = "qwen3:30b",
    ):
        self.model = model

    def extract_skills(
        self,
        text: str,
    ):
        response = chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """
Du analysierst Lebensläufe, Arbeitszeugnisse, Zertifikate und Stellenanzeigen.

Extrahiere nur Karriere-Skills, die durch den Text belegt sind.

Erlaubte Skills:
consulting
leadership
stakeholder_management
vendor_management
project_responsibility
change_management
security
architecture
cloud
automation
data

Gib ausschließlich JSON zurück.

Format:
[
  {
    "skill": "stakeholder_management",
    "confidence": 0.9,
    "evidence": "Koordination interner und externer Teams."
  }
]
""",
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            keep_alive="30m",
        )

        return parse_llm_skill_response(
            response.message.content
        )