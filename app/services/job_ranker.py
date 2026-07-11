from app.models.job import Job
from app.services.scorer import JobScorer


class JobRanker:
    def __init__(self, scorer: JobScorer):
        self.scorer = scorer

    def rank(self, jobs: list[Job]):
        results = []

        for job in jobs:
            result = self.scorer.score(job)

            results.append(
                {
                    "job": job,
                    "score": result.total_score,
                    "reasons": result.reasons,
                }
            )

        results.sort(key=lambda item: item["score"], reverse=True)

        return results