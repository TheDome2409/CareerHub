from pydantic import BaseModel
from typing import List, Optional


class CompanyIntel(BaseModel):
    kununu_rating: Optional[float] = None
    kununu_reviews: Optional[int] = None
    growth: bool = False
    innovation: bool = False
    development: bool = False
    red_flags: List[str] = []


class Job(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    work_model: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description: str = ""
    url: Optional[str] = None

    industries: List[str] = []
    employment_models: List[str] = []
    requirements: List[str] = []

    detected_keywords: List[str] = []
    career_tags: List[str] = []

    company_intel: CompanyIntel = CompanyIntel()