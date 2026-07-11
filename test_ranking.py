import json

from app.core.config_loader import load_profile, load_scoring
from app.sources.json_source import JsonSource
from app.services.scorer import JobScorer
from app.services.job_ranker import JobRanker


def test_old_app_ranker_ranks_synthetic_jobs(tmp_path):
    profile = load_profile("config/profile.example.yaml")
    scoring = load_scoring("config/scoring.example.yaml")
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(
        json.dumps(
            [
                {
                    "title": "IT Project Coordinator",
                    "company": "Example Technologies GmbH",
                    "description": "Synthetic public test job.",
                    "work_model": "remote",
                    "salary_max": 80000,
                    "career_tags": ["project_management"],
                },
                {
                    "title": "Legacy Support",
                    "company": "Example Support GmbH",
                    "description": "Synthetic lower-priority test job.",
                    "work_model": "onsite",
                },
            ]
        ),
        encoding="utf-8",
    )

    jobs = JsonSource(str(jobs_file)).load_jobs()
    scorer = JobScorer(profile.profile, scoring)
    ranker = JobRanker(scorer)

    results = ranker.rank(jobs)

    assert len(results) == 2
    assert results[0]["job"].company == "Example Technologies GmbH"
    assert results[0]["score"] >= results[1]["score"]
