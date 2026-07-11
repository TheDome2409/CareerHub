import json

from app.sources.json_source import JsonSource


def test_json_source_loads_synthetic_jobs(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(
        json.dumps(
            [
                {
                    "title": "IT Project Coordinator",
                    "company": "Example Technologies GmbH",
                    "description": "Synthetic public test job.",
                    "work_model": "remote",
                }
            ]
        ),
        encoding="utf-8",
    )

    jobs = JsonSource(str(jobs_file)).load_jobs()

    assert len(jobs) == 1
    assert jobs[0].title == "IT Project Coordinator"
    assert jobs[0].company == "Example Technologies GmbH"
