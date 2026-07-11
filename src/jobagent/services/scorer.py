from typing import List

from jobagent.models.job import Job
from jobagent.models.score_result import ScoreResult
from jobagent.services.competency_service import (
    compare_competencies,
    extract_job_competencies,
    extract_profile_competencies,
)
from jobagent.services.job_skill_service import calculate_skill_match


DEFAULT_SKILL_SCORE_WEIGHT = 25
MAX_COMPETENCY_SCORE = 10
BELOW_PROFILE_MINIMUM_SALARY_SCORE = -10
LOW_SKILL_MATCH_THRESHOLD = 0.2
DEVELOPER_ROLE_MISMATCH_PENALTY = -25
SENIOR_ENGINEERING_MISMATCH_PENALTY = -30
SUPPORT_ROLE_MISMATCH_PENALTY = -15

DEVELOPER_CORE_ROLE_PATTERNS = [
    "software engineer",
    "software developer",
    "full stack engineer",
    "full stack developer",
    "backend engineer",
    "backend developer",
    "frontend engineer",
    "frontend developer",
    "rails engineer",
    "ruby developer",
    "web developer",
    "mobile developer",
    "site reliability engineer",
    "devops engineer",
]

SENIOR_ENGINEERING_PATTERNS = [
    "tech lead",
    "technical lead",
    "senior",
    "principal",
    "staff engineer",
    "lead engineer",
]

SUPPORT_ROLE_PATTERNS = [
    "helpdesk",
    "first level support",
    "1st level support",
    "support engineer",
    "support specialist",
]

EXCLUSION_ALIASES = {
    "banking": [
        "banking",
        "bank",
        "banken",
        "finanzbranche",
        "financial services",
    ],
    "military": [
        "military",
        "militaer",
        "militar",
        "bundeswehr",
        "verteidigung",
    ],
    "defense": [
        "defense",
        "defence",
        "verteidigung",
        "verteidigungsindustrie",
        "ruestung",
        "rüstung",
    ],
    "temporary_work": [
        "temporary work",
        "zeitarbeit",
        "arbeitnehmerueberlassung",
        "arbeitnehmerüberlassung",
        "arbeitnehmerberlassung",
        "personaldienstleister",
    ],
    "labour_leasing": [
        "labour leasing",
        "labor leasing",
        "arbeitnehmerueberlassung",
        "arbeitnehmerüberlassung",
        "arbeitnehmerberlassung",
        "zeitarbeit",
    ],
    "labor_leasing": [
        "labour leasing",
        "labor leasing",
        "arbeitnehmerueberlassung",
        "arbeitnehmerüberlassung",
        "arbeitnehmerberlassung",
        "zeitarbeit",
    ],
    "security_clearance": [
        "security clearance",
        "sicherheitsueberpruefung",
        "sicherheitsüberprüfung",
        "sicherheitsberprfung",
        "sicherheitsfreigabe",
        "ue2",
        "ue3",
        "ü2",
        "ü3",
    ],
}


class JobScorer:
    def __init__(self, profile, scoring):
        self.profile = profile
        self.scoring = scoring

    def score(self, job: Job) -> ScoreResult:
        score = 0
        reasons = []
        role_score = 0
        work_model_score = 0
        salary_score = 0
        career_score = 0
        employer_score = 0
        skill_score = 0
        competency_score = 0
        role_mismatch_penalty = 0
        matched_skills = set()
        missing_skills = set()
        skill_match_ratio = 0.0
        competency_match_ratio = 0.0

        blocked_reasons = self._check_hard_exclusions(job)

        if blocked_reasons:
            return ScoreResult(
                total_score=-100,
                reasons=blocked_reasons,
            )

        role_score, matched_role = self._score_role_fit(job)
        score += role_score

        if role_score:
            reasons.append(
                f"Role match '{matched_role}': +{role_score}"
            )

        if job.work_model:
            work_model_score = self.scoring.work_model.get(
                job.work_model,
                0,
            )

            score += work_model_score

            if work_model_score:
                reasons.append(
                    f"Work model '{job.work_model}': +{work_model_score}"
                )

        salary_score = self._score_salary(job)
        score += salary_score

        salary = job.salary_max or job.salary_min

        if salary is not None:
            salary_prefix = "+" if salary_score >= 0 else ""
            reasons.append(
                f"Salary {salary:,} EUR: "
                f"{salary_prefix}{salary_score}".replace(
                    ",",
                    ".",
                )
            )

        career_score, career_reasons = self._score_career_fit(job)
        score += career_score

        if career_score:
            reasons.append(
                f"Career fit: +{career_score}"
            )

            for reason in career_reasons:
                reasons.append(
                    f"  - {reason}"
                )

        (
            skill_score,
            matched_skills,
            missing_skills,
            skill_match_ratio,
        ) = self._score_skill_fit(job)
        score += skill_score

        if matched_skills or missing_skills:
            matched_count = len(matched_skills)
            total_count = matched_count + len(missing_skills)
            reasons.append(
                f"Skill fit: {matched_count}/{total_count} "
                f"matched (+{skill_score})"
            )

        (
            role_mismatch_penalty,
            role_mismatch_reason,
        ) = self._score_role_mismatch_penalty(
            job,
            skill_match_ratio,
        )
        score += role_mismatch_penalty

        if role_mismatch_penalty:
            reasons.append(
                "Role Mismatch Penalty: "
                f"{role_mismatch_penalty} ({role_mismatch_reason})"
            )

        (
            competency_score,
            competency_match_ratio,
        ) = self._score_competency_fit(job)
        score += competency_score

        if competency_score:
            reasons.append(
                f"Competency Score: +{competency_score}"
            )
            reasons.append(
                "  - CareerHub erkennt uebertragbare Kompetenzen, "
                "die ueber den direkten Skill-Match hinausgehen."
            )

        employer_score = self._score_employer(job)
        score += employer_score

        if employer_score:
            reasons.append(
                f"Employer score: +{employer_score}"
            )

        return ScoreResult(
            total_score=score,
            reasons=reasons,
            role_score=role_score,
            work_model_score=work_model_score,
            salary_score=salary_score,
            career_score=career_score,
            employer_score=employer_score,
            skill_score=skill_score,
            competency_score=competency_score,
            role_mismatch_penalty=role_mismatch_penalty,
            matched_skills=sorted(matched_skills),
            missing_skills=sorted(missing_skills),
            skill_match_ratio=skill_match_ratio,
            competency_match_ratio=competency_match_ratio,
        )

    def _check_hard_exclusions(
        self,
        job: Job,
    ) -> List[str]:

        reasons = []
        hard_exclusions = self._combined_hard_exclusions()
        job_text = self._job_search_text(
            job
        )

        for industry in job.industries:
            if self._matches_exclusion(
                industry,
                hard_exclusions["industries"],
            ):
                reasons.append(
                    f"Hard exclusion: industry '{industry}'"
                )

        for model in job.employment_models:
            if self._matches_exclusion(
                model,
                hard_exclusions["employment_models"],
            ):
                reasons.append(
                    f"Hard exclusion: employment model '{model}'"
                )

        for requirement in job.requirements:
            if self._matches_exclusion(
                requirement,
                hard_exclusions["requirements"],
            ):
                reasons.append(
                    f"Hard exclusion: requirement '{requirement}'"
                )

        for category, exclusions in hard_exclusions.items():
            for exclusion in exclusions:
                if self._matches_exclusion(
                    job_text,
                    [exclusion],
                ):
                    reasons.append(
                        f"Hard exclusion: {category} '{exclusion}'"
                    )

        reasons = list(
            dict.fromkeys(reasons)
        )

        return reasons

    def _profile_object(self):
        return getattr(
            self.profile,
            "profile",
            self.profile,
        )

    def _combined_hard_exclusions(self) -> dict[str, list[str]]:
        profile = self._profile_object()
        profile_exclusions = getattr(
            profile,
            "exclusions",
            None,
        )
        scoring_exclusions = self.scoring.hard_exclusions

        return {
            "industries": list(scoring_exclusions.industries)
            + list(
                getattr(profile_exclusions, "industries", []) or []
            ),
            "employment_models": list(
                scoring_exclusions.employment_models
            )
            + list(
                getattr(
                    profile_exclusions,
                    "employment_models",
                    [],
                )
                or []
            ),
            "requirements": list(scoring_exclusions.requirements)
            + list(
                getattr(profile_exclusions, "requirements", []) or []
            ),
        }

    def _matches_exclusion(
        self,
        value: str,
        exclusions: list[str],
    ) -> bool:
        normalized_value = self._normalize_exclusion_text(
            value
        )

        if not normalized_value:
            return False

        for exclusion in exclusions:
            for term in self._exclusion_terms(exclusion):
                normalized_exclusion = self._normalize_exclusion_text(
                    term
                )

                if not normalized_exclusion:
                    continue

                if (
                    normalized_value == normalized_exclusion
                    or normalized_exclusion in normalized_value
                    or normalized_value in normalized_exclusion
                ):
                    return True

        return False

    def _normalize_exclusion_text(
        self,
        value: str,
    ) -> str:
        value = str(value or "").strip().lower()
        replacements = {
            "ä": "ae",
            "ö": "oe",
            "ü": "ue",
            "ß": "ss",
            "_": " ",
            "-": " ",
            "/": " ",
        }

        for source, target in replacements.items():
            value = value.replace(
                source,
                target,
            )

        return " ".join(
            value.split()
        )

    def _exclusion_terms(
        self,
        exclusion: str,
    ) -> list[str]:
        normalized = self._normalize_exclusion_text(
            exclusion
        )
        key = normalized.replace(
            " ",
            "_",
        )
        terms = [
            exclusion,
            normalized,
            key,
        ]
        terms.extend(
            EXCLUSION_ALIASES.get(key, [])
        )

        return list(
            dict.fromkeys(
                str(term)
                for term in terms
                if str(term).strip()
            )
        )

    def _job_search_text(
        self,
        job: Job,
    ) -> str:
        values = [
            job.title,
            job.company,
            job.location,
            job.work_model,
            job.description,
        ]
        values.extend(
            job.industries
        )
        values.extend(
            job.employment_models
        )
        values.extend(
            job.requirements
        )
        values.extend(
            job.detected_keywords
        )
        values.extend(
            job.career_tags
        )

        return " ".join(
            str(value)
            for value in values
            if value
        )

    def _normalized_role_text(
        self,
        value: str | None,
    ) -> str:
        return self._normalize_exclusion_text(
            value or ""
        )

    def _text_contains_any(
        self,
        text: str,
        patterns: list[str],
    ) -> bool:
        normalized = self._normalized_role_text(
            text
        )

        return any(
            self._normalized_role_text(pattern) in normalized
            for pattern in patterns
        )

    def _profile_has_developer_target_role(self) -> bool:
        profile = self._profile_object()
        preferred_roles = getattr(
            profile,
            "preferred_roles",
            [],
        ) or []

        return any(
            self._text_contains_any(
                role,
                DEVELOPER_CORE_ROLE_PATTERNS,
            )
            for role in preferred_roles
        )

    def _score_role_mismatch_penalty(
        self,
        job: Job,
        skill_match_ratio: float,
    ) -> tuple[int, str | None]:
        title = job.title or ""
        has_developer_core = self._text_contains_any(
            title,
            DEVELOPER_CORE_ROLE_PATTERNS,
        )
        has_support_core = self._text_contains_any(
            title,
            SUPPORT_ROLE_PATTERNS,
        )

        if not has_developer_core and not has_support_core:
            return 0, None

        if self._profile_has_developer_target_role():
            return 0, None

        if skill_match_ratio >= LOW_SKILL_MATCH_THRESHOLD:
            return 0, None

        if has_support_core:
            return (
                SUPPORT_ROLE_MISMATCH_PENALTY,
                "Support-Kernrolle passt nicht zum Zielprofil",
            )

        if self._text_contains_any(
            title,
            SENIOR_ENGINEERING_PATTERNS,
        ):
            return (
                SENIOR_ENGINEERING_MISMATCH_PENALTY,
                "Senior-/Lead-Engineering-Kernrolle passt nicht zum Zielprofil",
            )

        return (
            DEVELOPER_ROLE_MISMATCH_PENALTY,
            "Developer-/Engineering-Kernrolle passt nicht zum Zielprofil",
        )

    def _score_role_fit(
        self,
        job: Job,
    ) -> tuple[int, str | None]:

        title = job.title.lower()

        role_patterns = {
            "IT Project Manager": [
                "it project manager",
                "it projektmanager",
                "projektmanager für it projekte",
                "projektmanager für it-projekte",
                "projektmanager it",
                "projektleiter it",
            ],
            "Manager Digitalisierung": [
                "manager digitalisierung",
                "digitalisierung",
                "digital transformation",
                "transformationsmanager",
                "prozessoptimierung",
                "process optimization",
            ],
            "AI Manager": [
                "ai manager",
                "ki manager",
                "head of ai",
                "ai lead",
                "ki lead",
            ],
            "Technical Consultant": [
                "technical consultant",
                "solution consultant",
                "it consultant",
                "technical advisor",
            ],
        }

        best_score = 0
        best_role = None

        for role, role_score in self.scoring.roles.items():

            patterns = role_patterns.get(
                role,
                [role.lower()],
            )

            for pattern in patterns:

                if pattern in title:

                    if role_score > best_score:
                        best_score = role_score
                        best_role = role

        return best_score, best_role

    def _score_career_fit(
        self,
        job: Job,
    ) -> tuple[int, List[str]]:

        total = 0
        reasons = []

        for tag in job.career_tags:

            tag_score = self.scoring.career.get(
                tag,
                0,
            )

            if tag_score:
                total += tag_score

                reasons.append(
                    f"{tag}: +{tag_score}"
                )

        capped_total = min(
            total,
            self.scoring.weights.career_fit,
        )

        if total > capped_total:
            reasons.append(
                f"career score capped at "
                f"{self.scoring.weights.career_fit}"
            )

        return capped_total, reasons

    def _profile_skill_tags(self) -> set[str]:
        profile = self._profile_object()

        return {
            str(skill).strip()
            for skill in getattr(profile, "skills", [])
            if str(skill).strip()
        }

    def _skill_score_weight(self) -> int:
        weights = getattr(
            self.scoring,
            "weights",
            None,
        )

        return int(
            getattr(
                weights,
                "skill_fit",
                DEFAULT_SKILL_SCORE_WEIGHT,
            )
            or DEFAULT_SKILL_SCORE_WEIGHT
        )

    def _score_skill_fit(
        self,
        job: Job,
    ) -> tuple[int, set[str], set[str], float]:
        profile_tags = self._profile_skill_tags()

        if not profile_tags:
            return 0, set(), set(), 0.0

        matched_skills, missing_skills, match_ratio = calculate_skill_match(
            profile_tags,
            job.description,
        )

        if not matched_skills and not missing_skills:
            return 0, set(), set(), 0.0

        skill_score = round(
            match_ratio * self._skill_score_weight()
        )

        return (
            skill_score,
            matched_skills,
            missing_skills,
            match_ratio,
        )

    def _score_competency_fit(
        self,
        job: Job,
    ) -> tuple[int, float]:
        profile_competencies = extract_profile_competencies(
            self.profile
        )
        job_competencies = extract_job_competencies(
            job
        )
        result = compare_competencies(
            profile_competencies,
            job_competencies,
        )
        match_ratio = float(
            result.get("competency_match_ratio") or 0.0
        )
        competency_score = self._competency_score_from_ratio(
            match_ratio
        )

        return competency_score, match_ratio

    def _competency_score_from_ratio(
        self,
        match_ratio: float,
    ) -> int:
        return min(
            MAX_COMPETENCY_SCORE,
            round(match_ratio * MAX_COMPETENCY_SCORE),
        )

    def _score_employer(
        self,
        job: Job,
    ) -> int:

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
            total += self.scoring.red_flags.get(
                flag,
                0,
            )

        return min(
            total,
            self.scoring.weights.employer,
        )

    def _score_salary(
        self,
        job: Job,
    ) -> int:

        salary = job.salary_max or job.salary_min

        if salary is None:
            return 0

        profile_salary = getattr(
            self._profile_object(),
            "salary",
            None,
        )
        minimum_salary = int(
            getattr(profile_salary, "minimum", 0) or 0
        )
        below_minimum = (
            minimum_salary > 0
            and salary < minimum_salary
        )

        if salary >= 100000:
            score = self.scoring.salary.get(
                "above_100k",
                0,
            )
        elif salary >= 90000:
            score = self.scoring.salary.get(
                "between_90k_100k",
                0,
            )
        elif salary >= 80000:
            score = self.scoring.salary.get(
                "between_80k_90k",
                0,
            )
        elif salary >= 70000:
            score = self.scoring.salary.get(
                "between_70k_80k",
                0,
            )
        elif salary >= 60000:
            score = self.scoring.salary.get(
                "between_60k_70k",
                0,
            )
        else:
            score = self.scoring.salary.get(
                "below_60k",
                0,
            )

        if below_minimum:
            return min(
                score,
                BELOW_PROFILE_MINIMUM_SALARY_SCORE,
            )

        return score
        
