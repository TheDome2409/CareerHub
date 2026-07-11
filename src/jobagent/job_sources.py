from abc import ABC, abstractmethod

from jobagent.models.job import Job


class JobSource(ABC):

    @abstractmethod
    def load_jobs(self) -> list[Job]:
        pass
