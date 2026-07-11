from abc import ABC, abstractmethod

from app.models.job import Job


class JobSource(ABC):

    @abstractmethod
    def load_jobs(self) -> list[Job]:
        pass