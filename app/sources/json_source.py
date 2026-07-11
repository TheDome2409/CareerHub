import json

from pathlib import Path

from app.models.job import Job

from app.job_sources import JobSource


class JsonSource(JobSource):

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def load_jobs(self) -> list[Job]:

        with open(
            self.file_path,
            "r",
            encoding="utf-8"
        ) as file:

            raw_jobs = json.load(file)

        return [
            Job(**job)
            for job in raw_jobs
        ]