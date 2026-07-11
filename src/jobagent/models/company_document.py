from pydantic import BaseModel


class CompanyDocument(BaseModel):
    id: int | None = None
    company_id: int
    source_id: int
    url: str
    title: str | None = None
    content_type: str | None = None
    mime_type: str | None = None
    charset: str | None = None
    content_hash: str | None = None
    content_text: str = ""
    status_code: int | None = None
    content_size: int = 0
    etag: str | None = None
    last_modified: str | None = None
    fetched_at: str
    request_duration_ms: int | None = None
