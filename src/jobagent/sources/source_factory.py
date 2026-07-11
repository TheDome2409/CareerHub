from jobagent.sources.json_source import JsonSource
from jobagent.sources.rss_source import RssSource
from jobagent.sources.remotive_source import RemotiveSource
from jobagent.sources.source_config import SourceConfig
from jobagent.sources.bundesagentur_source import (
    BundesagenturSource,
)

class SourceFactory:

    @staticmethod
    def create(config: SourceConfig):
        if config.type == "json":
            if not config.path:
                raise ValueError("JSON source requires a path")

            return JsonSource(config.path)

        if config.type == "rss":
            if not config.url:
                raise ValueError("RSS source requires a url")

            return RssSource(
                url=config.url,
                default_company=config.default_company,
                default_work_model=config.default_work_model,
            )
        if config.type == "bundesagentur":
            return BundesagenturSource(
                keyword=config.query or "",
                location=config.location or "Deutschland",
                max_results=config.max_results or 50,
                published_since_days=config.published_since_days or 90,
            )

        if config.type == "remotive":
            return RemotiveSource(
                search=config.query,
                category=config.category,
                max_results=config.max_results or 50,
            )

        raise ValueError(
            f"Unknown source type: {config.type}"
        )
