import os

import requests

from jobagent.models.job import Job
from jobagent.services.keyword_detector import detect_tags


DEBUG = False


class BundesagenturSource:
    BASE_URL = (
        "https://rest.arbeitsagentur.de/"
        "jobboerse/jobsuche-service/pc/v4/jobs"
    )

    def __init__(
        self,
        keyword: str,
        location: str = "Deutschland",
        max_results: int = 50,
        published_since_days: int = 90,
    ):
        self.keyword = keyword
        self.location = location
        self.max_results = max_results
        self.published_since_days = published_since_days

    def load(self) -> list[Job]:
        api_key = os.getenv("BUNDESAGENTUR_API_KEY")
        if not api_key:
            raise RuntimeError(
                "BUNDESAGENTUR_API_KEY is not configured. Set the public "
                "Bundesagentur jobsuche API client identifier in the "
                "environment before loading this source."
            )

        headers = {
            "X-API-Key": api_key,
        }

        params = {
            "was": self.keyword,
            "wo": self.location,
            "page": 1,
            "size": min(self.max_results, 100),
            "veroeffentlichtseit": min(
                self.published_since_days,
                100,
            ),
            "angebotsart": 1,
            "zeitarbeit": "false",
        }

        response = requests.get(
            self.BASE_URL,
            headers=headers,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        jobs = []

        for item in data.get("stellenangebote", []):
            title = (
                item.get("titel")
                or item.get("beruf")
                or "Ohne Titel"
            )

            profession = item.get("beruf") or ""
            company = item.get("arbeitgeber") or "Unbekannt"

            work_location = (
                item.get("arbeitsort", {}).get("ort")
                or ""
            )

            published_at = (
                item.get("aktuelleVeroeffentlichungsdatum")
                or ""
            )

            url = item.get("externeUrl")
            refnr = item.get("refnr") or ""

            description = "\n".join(
                [
                    title,
                    profession,
                    company,
                    work_location,
                    f"Veröffentlicht: {published_at}",
                    f"Referenznummer: {refnr}",
                ]
            )

            combined_text = " ".join(
                [
                    title,
                    profession,
                    company,
                    work_location,
                    description,
                ]
            )

            career_tags = detect_tags(
                combined_text
            )

            jobs.append(
                Job(
                    title=title,
                    company=company,
                    work_model=work_location,
                    description=description,
                    url=url,
                    source_name="Bundesagentur",
                    source_type="bundesagentur",
                    career_tags=career_tags,
                    detected_keywords=career_tags,
                )
            )

        if DEBUG:
            print(
                f"Bundesagentur: {len(jobs)} Jobs erzeugt"
            )

        return jobs
