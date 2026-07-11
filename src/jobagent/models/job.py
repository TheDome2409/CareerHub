from pydantic import BaseModel, Field
from typing import List, Optional


class CompanyIntel(BaseModel):
    kununu_rating: Optional[float] = None
    kununu_reviews: Optional[int] = None
    growth: bool = False
    innovation: bool = False
    development: bool = False
    red_flags: List[str] = Field(default_factory=list)


class Job(BaseModel):
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    work_model: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description: str = ""
    url: Optional[str] = None
    source_name: Optional[str] = None
    source_type: Optional[str] = None
    query_source: Optional[str] = None

    industries: List[str] = Field(default_factory=list)
    employment_models: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)

    detected_keywords: List[str] = Field(default_factory=list)
    career_tags: List[str] = Field(default_factory=list)

    company_intel: CompanyIntel = Field(default_factory=CompanyIntel)
