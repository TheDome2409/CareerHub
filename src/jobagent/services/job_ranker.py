from jobagent.models.job import Job
from jobagent.services.scorer import JobScorer


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
                    "skill_score": result.skill_score,
                    "competency_score": result.competency_score,
                    "role_score": result.role_score,
                    "work_model_score": result.work_model_score,
                    "salary_score": result.salary_score,
                    "career_score": result.career_score,
                    "employer_score": result.employer_score,
                    "role_mismatch_penalty": (
                        result.role_mismatch_penalty
                    ),
                    "matched_skills": result.matched_skills,
                    "missing_skills": result.missing_skills,
                    "skill_match_ratio": result.skill_match_ratio,
                    "competency_match_ratio": result.competency_match_ratio,
                }
            )

        results.sort(key=lambda item: item["score"], reverse=True)

        return results
