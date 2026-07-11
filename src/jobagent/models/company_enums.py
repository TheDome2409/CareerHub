from enum import Enum


class WorkModel(str, Enum):
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"


class SourcePerspective(str, Enum):
    SELF = "self"
    EXTERNAL = "external"
    NEUTRAL = "neutral"


class SourceType(str, Enum):
    COMPANY_WEBSITE = "company_website"
    CAREER_PAGE = "career_page"
    ABOUT_PAGE = "about_page"
    NEWS_PAGE = "news_page"
    PRESS_PAGE = "press_page"
    ANNUAL_REPORT = "annual_report"
    SUSTAINABILITY_REPORT = "sustainability_report"
    KUNUNU = "kununu"
    GLASSDOOR = "glassdoor"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"
    GITHUB = "github"
    BLOG = "blog"
    NORTH_DATA = "north_data"
    HANDELSREGISTER = "handelsregister"
    COMPANY_REGISTER = "company_register"
    OTHER = "other"


class BusinessDomain(str, Enum):
    ENERGY = "energy"
    RAIL = "rail"
    TELECOMMUNICATION = "telecommunication"
    HEALTHCARE = "healthcare"
    INDUSTRY = "industry"
    PUBLIC_SECTOR = "public_sector"
    FINANCE = "finance"
    EDUCATION = "education"
    RESEARCH = "research"
    MANUFACTURING = "manufacturing"
