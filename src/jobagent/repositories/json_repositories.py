import json
from pathlib import Path

from jobagent.models.global_skill_candidate import GlobalSkillCandidate
from jobagent.models.recommendation_outcome import RecommendationOutcome
from jobagent.models.recommendation_snapshot import RecommendationSnapshot


def _load_json_list(path: str | Path) -> list:
    path = Path(path)

    if not path.exists():
        return []

    raw_data = path.read_text(
        encoding="utf-8"
    ).strip()

    if not raw_data:
        return []

    try:
        data = json.loads(
            raw_data
        )
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    return data


def _write_json_list(path: str | Path, values: list) -> None:
    path = Path(path)
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(
            values,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _deduplicate_snapshots(snapshots: list[dict]) -> list[dict]:
    deduplicated = {}

    for snapshot in snapshots:
        recommendation_id = str(
            snapshot.get("recommendation_id", "") or ""
        )

        if not recommendation_id:
            continue

        deduplicated.setdefault(
            recommendation_id,
            snapshot,
        )

    return list(
        deduplicated.values()
    )


class JsonReviewQueueRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load_entries(self) -> list[dict]:
        return [
            item
            for item in _load_json_list(self.path)
            if isinstance(item, dict)
        ]

    def save_entries(self, entries: list[dict]) -> None:
        _write_json_list(
            self.path,
            entries,
        )

    def append_entry(self, entry: dict) -> list[dict]:
        entries = self.load_entries()
        entries.append(entry)
        self.save_entries(
            entries
        )

        return entries

    def update_entry(self, entry: dict) -> list[dict]:
        entries = self.load_entries()
        entry_key = str(
            entry.get("key")
            or entry.get("id")
            or entry.get("review_item_key")
            or ""
        )

        if not entry_key:
            entries.append(entry)
            self.save_entries(entries)
            return entries

        updated = False

        for index, current in enumerate(entries):
            current_key = str(
                current.get("key")
                or current.get("id")
                or current.get("review_item_key")
                or ""
            )

            if current_key == entry_key:
                entries[index] = entry
                updated = True
                break

        if not updated:
            entries.append(entry)

        self.save_entries(entries)

        return entries


class JsonGlobalSkillCandidateRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load_candidates(self) -> list[GlobalSkillCandidate]:
        return [
            GlobalSkillCandidate.model_validate(item)
            for item in _load_json_list(self.path)
            if isinstance(item, dict)
        ]

    def save_candidates(self, candidates: list[GlobalSkillCandidate]) -> None:
        _write_json_list(
            self.path,
            [
                candidate.model_dump(mode="json")
                for candidate in candidates
            ],
        )


class JsonRecommendationSnapshotRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load_snapshots(self) -> list[RecommendationSnapshot]:
        return [
            RecommendationSnapshot.model_validate(item)
            for item in _load_json_list(self.path)
            if isinstance(item, dict)
        ]

    def save_snapshots(self, snapshots: list[RecommendationSnapshot]) -> None:
        _write_json_list(
            self.path,
            [
                snapshot.model_dump(mode="json")
                for snapshot in snapshots
            ],
        )

    def append_snapshot(self, snapshot: RecommendationSnapshot) -> None:
        snapshots = [
            item
            for item in _load_json_list(self.path)
            if isinstance(item, dict)
        ]
        snapshot_data = snapshot.model_dump(mode="json")
        recommendation_id = snapshot_data.get(
            "recommendation_id"
        )

        if not any(
            item.get("recommendation_id") == recommendation_id
            for item in snapshots
        ):
            snapshots.append(snapshot_data)

        _write_json_list(
            self.path,
            _deduplicate_snapshots(snapshots),
        )


class JsonRecommendationOutcomeRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load_outcomes(self) -> list[RecommendationOutcome]:
        return [
            RecommendationOutcome.model_validate(item)
            for item in _load_json_list(self.path)
            if isinstance(item, dict)
        ]

    def save_outcomes(self, outcomes: list[RecommendationOutcome]) -> None:
        _write_json_list(
            self.path,
            [
                outcome.model_dump(mode="json")
                for outcome in outcomes
            ],
        )

    def append_outcome(
        self,
        outcome: RecommendationOutcome,
    ) -> list[RecommendationOutcome]:
        outcomes = self.load_outcomes()
        outcomes.append(outcome)
        self.save_outcomes(
            outcomes
        )

        return outcomes

    def get_outcomes_for_recommendation(
        self,
        recommendation_id: str,
    ) -> list[RecommendationOutcome]:
        return [
            outcome
            for outcome in self.load_outcomes()
            if outcome.recommendation_id == recommendation_id
        ]
