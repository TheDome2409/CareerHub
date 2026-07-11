from pydantic import BaseModel


class ValidationSummary(BaseModel):
    total_recommendations: int = 0
    viewed_count: int = 0
    saved_count: int = 0
    applied_count: int = 0
    interview_count: int = 0
    offer_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    application_rate: float = 0.0
    interview_rate: float = 0.0
    offer_rate: float = 0.0
    acceptance_rate: float = 0.0
