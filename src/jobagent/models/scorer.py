from typing import List

from jobagent.models.job import Job
from jobagent.models.score_result import ScoreResult


class JobScorer:
    def __init__(self, profile, scoring):
        self.profile = profile
        self.scoring = scoring

    def score(self, job: Job) -> ScoreResult:
        score = 0
        reasons = []

        blocked_reasons = self._check_hard_exclusions(job)
        if blocked_reasons:
            return ScoreResult(total_score=-100, reasons=blocked_reasons)

        role_score = self.scoring.roles.get(job.title, 0)
        score += role_score
        if role_score:
            reasons.append(f"Role match: +{role_score}")

        if job.work_model:
            work_model_score = self.scoring.work_model.get(job.work_model, 0)
            score += work_model_score
            if work_model_score:
                reasons.append(f"Work model '{job.work_model}': +{work_model_score}")

        salary_score = self._score_salary(job)
        score += salary_score

        salary = job.salary_max or job.salary_min
        if salary is not None:
            reasons.append(
                f"Salary {salary:,} EUR: +{salary_score}".replace(",", ".")
            )

        career_score, career_reasons = self._score_career_fit(job)
        score += career_score
        if career_score:
            reasons.append(f"Career fit: +{career_score}")
            for reason in career_reasons:
                reasons.append(f"  - {reason}")

        employer_score = self._score_employer(job)
        score += employer_score
        if employer_score:
            reasons.append(f"Employer score: +{employer_score}")

        return ScoreResult(total_score=score, reasons=reasons)

    def _check_hard_exclusions(self, job: Job) -> List[str]:
        reasons = []

        for industry in job.industries:
            if industry in self.scoring.hard_exclusions.industries:
                reasons.append(f"Hard exclusion: industry '{industry}'")

        for model in job.employment_models:
            if model in self.scoring.hard_exclusions.employment_models:
                reasons.append(f"Hard exclusion: employment model '{model}'")

        for requirement in job.requirements:
            if requirement in self.scoring.hard_exclusions.requirements:
                reasons.append(f"Hard exclusion: requirement '{requirement}'")

        return reasons

    def _score_career_fit(self, job: Job) -> tuple[int, List[str]]:
        total = 0
        reasons = []

        for tag in job.career_tags:
            tag_score = self.scoring.career.get(tag, 0)

            if tag_score:
                total += tag_score
                reasons.append(f"{tag}: +{tag_score}")

        capped_total = min(total, self.scoring.weights.career_fit)

        if total > capped_total:
            reasons.append(
                f"career score capped at {self.scoring.weights.career_fit}"
            )

        return capped_total, reasons

    def _score_employer(self, job: Job) -> int:
        total = 0
        intel = job.company_intel

        if intel.kununu_rating is not None:
            rating = intel.kununu_rating

            if rating >= 4.3:
                total += self.scoring.employer.kununu.above_4_3
            elif rating >= 4.0:
                total += self.scoring.employer.kununu.above_4_0
            elif rating >= 3.7:
                total += self.scoring.employer.kununu.above_3_7
            elif rating < 3.0:
                total += self.scoring.employer.kununu.below_3_0
            elif rating < 3.5:
                total += self.scoring.employer.kununu.below_3_5

        if intel.growth:
            total += self.scoring.employer.growth

        if intel.innovation:
            total += self.scoring.employer.innovation

        if intel.development:
            total += self.scoring.employer.development

        for flag in intel.red_flags:
            total += self.scoring.red_flags.get(flag, 0)

        return min(total, self.scoring.weights.employer)

    def _score_salary(self, job: Job) -> int:
        salary = job.salary_max or job.salary_min

        if salary is None:
            return 0

        if salary >= 100000:
            return self.scoring.salary.get("above_100k", 0)

        if salary >= 90000:
            return self.scoring.salary.get("between_90k_100k", 0)

        if salary >= 80000:
            return self.scoring.salary.get("between_80k_90k", 0)

        if salary >= 70000:
            return self.scoring.salary.get("between_70k_80k", 0)

        if salary >= 60000:
            return self.scoring.salary.get("between_60k_70k", 0)

        return self.scoring.salary.get("below_60k", 0)