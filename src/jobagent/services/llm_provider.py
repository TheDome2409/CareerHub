from abc import ABC, abstractmethod


class LlmProvider(ABC):

    @abstractmethod
    def extract_skills(
        self,
        text: str,
    ):
        pass