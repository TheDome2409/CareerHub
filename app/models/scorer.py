from app.models.job import Job
from app.models.score_result import ScoreResult


class JobScorer:
    def __init__(self, profile, scoring):
        self.profile = profile
        self.scoring = scoring

    def score(self, job: Job) -> ScoreResult:
        score = 0
        reasons = []

        role_score = self.scoring.roles.get(job.title, 0)
        score += role_score

        if role_score:
            reasons.append(f"Role match: +{role_score}")

        if job.work_model == "remote":
            wm = self.scoring.work_model.get("remote", 0)
            score += wm
            reasons.append(f"Remote work: +{wm}")

        return ScoreResult(total_score=score, reasons=reasons)