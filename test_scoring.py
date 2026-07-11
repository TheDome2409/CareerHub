from app.core.config_loader import load_profile, load_scoring
from app.models.job import Job
from app.services.scorer import JobScorer
from app.models.job import Job, CompanyIntel


profile = load_profile("config/profile.example.yaml")
scoring = load_scoring("config/scoring.example.yaml")

scorer = JobScorer(profile.profile, scoring)

job_ok = Job(
    title="Manager Digitalisierung",
    company="Tech GmbH",
    work_model="remote"
)

job_blocked = Job(
    title="IT Project Manager",
    company="Defense GmbH",
    work_model="remote",
    industries=["defense"]
)
job_low = Job(
    title="Technical Consultant",
    company="Budget GmbH",
    work_model="hybrid",
    salary_min=55000,
    salary_max=58000
)

job_target = Job(
    title="Manager Digitalisierung",
    company="Tech GmbH",
    work_model="remote",
    salary_min=80000,
    salary_max=85000
)

job_dream = Job(
    title="AI Manager",
    company="Future Systems",
    work_model="remote",
    salary_min=110000,
    salary_max=125000,
    career_tags=[
        "ai",
        "leadership",
        "strategic_role",
        "innovation"
    ],
    company_intel=CompanyIntel(
        kununu_rating=4.4,
        kununu_reviews=120,
        growth=True,
        innovation=True,
        development=True
    )
)

job_target = Job(
    title="Manager Digitalisierung",
    company="Tech GmbH",
    work_model="remote",
    salary_min=80000,
    salary_max=85000,
    career_tags=[
        "digitalization",
        "project_responsibility",
        "strategic_role"
    ]
)
job_blocked = Job(
    title="IT Project Manager",
    company="Defense GmbH",
    work_model="remote",
    industries=["defense"]
)
job_dream = Job(
    title="AI Manager",
    company="Future Systems",
    work_model="remote",
    salary_min=110000,
    salary_max=125000,
    career_tags=[
        "ai",
        "leadership",
        "strategic_role",
        "innovation"
    ]
)
for job in [job_low, job_target, job_dream]:
    result = scorer.score(job)

    print(f"\n{job.title}")
    print(result.total_score)
    print(result.reasons)
result_ok = scorer.score(job_ok)
result_blocked = scorer.score(job_blocked)

print("OK Job:")
print(result_ok.total_score)
print(result_ok.reasons)

print("\nBlocked Job:")
print(result_blocked.total_score)
print(result_blocked.reasons)