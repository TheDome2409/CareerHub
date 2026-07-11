from jobagent.models.company import CompanyProfile
from jobagent.models.job import CompanyIntel, Job
from jobagent.services.competency_service import (
    extract_job_competencies,
)
from jobagent.services.job_intelligence_service import (
    analyze_job,
)


UNKNOWN_COMPANY = "Arbeitgeber unbekannt"


def _job_from_result(item) -> Job | None:
    if isinstance(item, Job):
        return item

    if isinstance(item, dict):
        job = item.get("job")

        if isinstance(job, Job):
            return job

    return None


def _company_name(job: Job) -> str:
    return (
        str(getattr(job, "company", "") or "").strip()
        or UNKNOWN_COMPANY
    )


def _add(values: set[str], value: str | None) -> None:
    value = str(value or "").strip()

    if value:
        values.add(value)


def _add_many(values: set[str], items) -> None:
    for item in items or []:
        _add(
            values,
            item,
        )


def _merge_company_intel(jobs: list[Job]) -> CompanyIntel:
    ratings = [
        job.company_intel.kununu_rating
        for job in jobs
        if job.company_intel.kununu_rating is not None
    ]
    reviews = [
        job.company_intel.kununu_reviews
        for job in jobs
        if job.company_intel.kununu_reviews is not None
    ]
    red_flags = []

    for job in jobs:
        for flag in job.company_intel.red_flags:
            if flag not in red_flags:
                red_flags.append(flag)

    return CompanyIntel(
        kununu_rating=(max(ratings) if ratings else None),
        kununu_reviews=(max(reviews) if reviews else None),
        growth=any(job.company_intel.growth for job in jobs),
        innovation=any(job.company_intel.innovation for job in jobs),
        development=any(job.company_intel.development for job in jobs),
        red_flags=red_flags,
    )


def aggregate_company(
    name: str,
    jobs: list[Job],
) -> CompanyProfile:
    locations = set()
    industries = set()
    work_models = set()
    detected_skills = set()
    detected_competencies = set()
    qualification_requirements = set()

    for job in jobs:
        _add(
            locations,
            job.location,
        )
        _add(
            work_models,
            job.work_model,
        )
        _add_many(
            industries,
            job.industries,
        )
        _add_many(
            detected_skills,
            job.detected_keywords,
        )
        _add_many(
            detected_skills,
            job.career_tags,
        )

        intelligence = getattr(
            job,
            "job_intelligence",
            None,
        ) or analyze_job(
            job
        )
        _add_many(
            detected_skills,
            intelligence.extracted_skills,
        )
        _add_many(
            detected_competencies,
            intelligence.extracted_competencies,
        )
        _add_many(
            qualification_requirements,
            intelligence.qualification_requirements,
        )
        _add_many(
            detected_competencies,
            extract_job_competencies(job).keys(),
        )

    return CompanyProfile(
        name=name,
        jobs=jobs,
        locations=sorted(locations, key=str.lower),
        industries=sorted(industries, key=str.lower),
        work_models=sorted(work_models, key=str.lower),
        detected_skills=sorted(detected_skills, key=str.lower),
        detected_competencies=sorted(
            detected_competencies,
            key=str.lower,
        ),
        qualification_requirements=sorted(
            qualification_requirements,
            key=str.lower,
        ),
        company_intel=_merge_company_intel(
            jobs
        ),
    )


def aggregate_companies(items) -> list[CompanyProfile]:
    grouped: dict[str, list[Job]] = {}

    for item in items or []:
        job = _job_from_result(
            item
        )

        if not job:
            continue

        grouped.setdefault(
            _company_name(job),
            [],
        ).append(job)

    return [
        aggregate_company(
            name,
            jobs,
        )
        for name, jobs in sorted(
            grouped.items(),
            key=lambda item: item[0].lower(),
        )
    ]
