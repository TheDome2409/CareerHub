import re

import requests

from jobagent.models.job import Job
from jobagent.services.keyword_detector import detect_tags


class RemotiveSource:
    BASE_URL = "https://remotive.com/api/remote-jobs"

    def __init__(
        self,
        search: str | None = None,
        category: str | None = None,
        max_results: int = 50,
    ):
        self.search = search
        self.category = category
        self.max_results = max_results

    def load(self) -> list[Job]:
        requested_limit = self.max_results
        params = {
            "limit": max(
                self.max_results,
                100,
            ),
        }

        if self.search:
            params["search"] = self.search

        if self.category:
            params["category"] = self.category

        response = requests.get(
            self.BASE_URL,
            params=params,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        jobs = []

        for item in data.get("jobs", []):
            title = item.get("title") or "Ohne Titel"
            company = item.get("company_name")
            description = item.get("description") or ""
            location = item.get("candidate_required_location")
            job_type = item.get("job_type")
            url = item.get("url")

            clean_description = re.sub(
                r"<[^>]+>",
                " ",
                description,
            )
            combined_text = " ".join(
                [
                    title,
                    company or "",
                    clean_description,
                    item.get("category") or "",
                ]
            )

            if not self._matches_search(
                combined_text
            ):
                continue

            career_tags = detect_tags(combined_text)

            jobs.append(
                Job(
                    title=title,
                    company=company,
                    location=location,
                    work_model="remote",
                    description=clean_description,
                    url=url,
                    source_name="Remotive",
                    source_type="remotive",
                    employment_models=(
                        [job_type]
                        if job_type
                        else []
                    ),
                    career_tags=career_tags,
                    detected_keywords=career_tags,
                )
            )

            if len(jobs) >= requested_limit:
                break

        return jobs

    def _matches_search(self, text: str) -> bool:
        if not self.search:
            return True

        normalized_text = text.lower()
        terms = [
            term
            for term in re.split(
                r"\s+",
                self.search.lower(),
            )
            if term
        ]

        return all(
            term in normalized_text
            for term in terms
        )
