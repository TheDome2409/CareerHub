from pydantic import BaseModel, Field


class Competency(BaseModel):
    name: str
    description: str = ""
    related_competencies: list[str] = Field(default_factory=list)
    source_skills: list[str] = Field(default_factory=list)
