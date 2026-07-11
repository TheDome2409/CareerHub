from pydantic import BaseModel
from typing import List, Dict


class Location(BaseModel):
    city: str
    country: str


class WorkModel(BaseModel):
    preferred: List[str]
    acceptable: List[str] = []
    public_transport_required: bool = False


class Salary(BaseModel):
    minimum: int
    target: int
    dream: int


class CareerGoals(BaseModel):
    short_term: List[str] = []
    mid_term: List[str] = []
    long_term: List[str] = []


class Exclusions(BaseModel):
    industries: List[str] = []
    employment_models: List[str] = []
    requirements: List[str] = []


class EmployerPreferences(BaseModel):
    positive: List[str] = []
    negative: List[str] = []


class CompanyPreferences(BaseModel):
    preferred_size: List[str] = []
    acceptable_size: List[str] = []


class ScoringPreferences(BaseModel):
    leadership_weight: str = "medium"
    ai_weight: str = "medium"
    digitalization_weight: str = "medium"
    project_management_weight: str = "medium"
    consulting_weight: str = "medium"
    infrastructure_weight: str = "medium"
    edi_weight: str = "low"
    training_weight: str = "low"


class Profile(BaseModel):
    name: str
    location: Location
    work_model: WorkModel
    salary: Salary
    preferred_roles: List[str]
    skills: List[str] = []
    certifications: List[str] = []
    languages: Dict[str, str] = {}
    career_goals: CareerGoals
    interests: List[str] = []
    exclusions: Exclusions
    employer_preferences: EmployerPreferences = EmployerPreferences()
    company_preferences: CompanyPreferences = CompanyPreferences()
    scoring_preferences: ScoringPreferences = ScoringPreferences()


class ProfileConfig(BaseModel):
    profile: Profile