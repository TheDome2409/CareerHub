from pydantic import BaseModel
from typing import Dict, List


class Weights(BaseModel):
    role_fit: int
    career_fit: int
    work_model: int
    salary: int
    employer: int


class KununuScores(BaseModel):
    above_4_3: int
    above_4_0: int
    above_3_7: int
    below_3_5: int
    below_3_0: int


class EmployerScores(BaseModel):
    kununu: KununuScores
    growth: int = 0
    innovation: int = 0
    development: int = 0


class HardExclusions(BaseModel):
    industries: List[str] = []
    employment_models: List[str] = []
    requirements: List[str] = []


class ScoringConfig(BaseModel):
    weights: Weights
    roles: Dict[str, int]
    career: Dict[str, int]
    work_model: Dict[str, int]
    salary: Dict[str, int]
    employer: EmployerScores
    red_flags: Dict[str, int] = {}
    hard_exclusions: HardExclusions