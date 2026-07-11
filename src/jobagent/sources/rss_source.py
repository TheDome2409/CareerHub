import feedparser

from jobagent.models.job import Job
from jobagent.services.keyword_detector import detect_tags


DEBUG = False


class RssSource:

    def __init__(
        self,
        url: str,
        default_company: str | None = None,
        default_work_model: str | None = None,
    ):
        self.url = url
        self.source_name = default_company or "RSS"
        self.default_work_model = default_work_model

    def load(self) -> list[Job]:
        feed = feedparser.parse(self.url)

        jobs = []

        for entry in feed.entries:
            title = getattr(entry, "title", "Ohne Titel")
            link = getattr(entry, "link", None)
            summary = getattr(entry, "summary", "")
            company = getattr(entry, "author", None)

            if company == self.source_name:
                company = None

            combined_text = f"{title} {summary}"
            career_tags = detect_tags(combined_text)

            if DEBUG:
                print(
                    f"[DEBUG] {title}: "
                    f"{', '.join(career_tags) if career_tags else 'keine Tags'}"
                )

            jobs.append(
                Job(
                    title=title,
                    company=company,
                    work_model=self.default_work_model,
                    description=summary,
                    url=link,
                    source_name=self.source_name,
                    source_type="rss",
                    career_tags=career_tags,
                    detected_keywords=career_tags,
                )
            )

        return jobs
