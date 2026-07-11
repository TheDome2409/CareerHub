import json
from pathlib import Path

from jobagent.models.job import Job


class JsonSource:

    def __init__(self, path: str):
        self.path = Path(path)

    def load(self) -> list[Job]:
        if not self.path.exists():
            raise FileNotFoundError(
                f"JSON source file not found: {self.path}"
            )

        with open(self.path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return [
            Job.model_validate(item)
            for item in data
        ]