from pathlib import Path
from typing import Protocol

from jobagent.models.global_skill_candidate import GlobalSkillCandidate
from jobagent.models.recommendation_outcome import RecommendationOutcome
from jobagent.models.recommendation_snapshot import RecommendationSnapshot


class ReviewQueueRepository(Protocol):
    def load_entries(self) -> list[dict]:
        ...

    def save_entries(self, entries: list[dict]) -> None:
        ...

    def append_entry(self, entry: dict) -> list[dict]:
        ...

    def update_entry(self, entry: dict) -> list[dict]:
        ...


class GlobalSkillCandidateRepository(Protocol):
    def load_candidates(self) -> list[GlobalSkillCandidate]:
        ...

    def save_candidates(self, candidates: list[GlobalSkillCandidate]) -> None:
        ...


class RecommendationSnapshotRepository(Protocol):
    def load_snapshots(self) -> list[RecommendationSnapshot]:
        ...

    def save_snapshots(self, snapshots: list[RecommendationSnapshot]) -> None:
        ...

    def append_snapshot(self, snapshot: RecommendationSnapshot) -> None:
        ...


class RecommendationOutcomeRepository(Protocol):
    def load_outcomes(self) -> list[RecommendationOutcome]:
        ...

    def save_outcomes(self, outcomes: list[RecommendationOutcome]) -> None:
        ...

    def append_outcome(
        self,
        outcome: RecommendationOutcome,
    ) -> list[RecommendationOutcome]:
        ...

    def get_outcomes_for_recommendation(
        self,
        recommendation_id: str,
    ) -> list[RecommendationOutcome]:
        ...


class TaxonomyRepository(Protocol):
    def load_aliases(self) -> dict[str, set[str]]:
        ...

    def load_competencies(self) -> dict:
        ...

    def load_qualifications(self) -> dict:
        ...

    def load_job_intelligence_patterns(self) -> dict:
        ...


PathLike = str | Path
