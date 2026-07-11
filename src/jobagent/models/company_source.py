from pydantic import BaseModel

from jobagent.models.company_enums import SourceType


class CompanySource(BaseModel):
    id: int | None = None
    company_id: int
    source_type: SourceType | str
    url: str
    title: str
    description: str | None = None
    enabled: bool = True
    priority: int = 3
    last_checked: str | None = None
    last_success: str | None = None
    etag: str | None = None
    content_hash: str | None = None
    notes: str | None = None
    created_at: str
