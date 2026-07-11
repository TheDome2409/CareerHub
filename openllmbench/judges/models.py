from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from openllmbench.core.models import VersionedModel


class JudgeMode(str, Enum):
    HUMAN = "human"
    LLM = "llm"
    MULTI_JUDGE = "multi_judge"
    CONSENSUS = "consensus"


class ConsensusStrategy(str, Enum):
    NONE = "none"
    MAJORITY = "majority"
    AVERAGE = "average"
    WEIGHTED_AVERAGE = "weighted_average"
    UNANIMOUS = "unanimous"
    HUMAN_OVERRIDE = "human_override"


@dataclass(frozen=True)
class JudgeCriterion(VersionedModel):
    label: str = ""
    scale_min: float = 0.0
    scale_max: float = 10.0
    weight: float = 1.0
    required: bool = True


@dataclass(frozen=True)
class JudgeRubric(VersionedModel):
    name: str = ""
    criteria: list[JudgeCriterion] = field(default_factory=list)
    scoring_notes: list[str] = field(default_factory=list)
    supported_modes: list[str] = field(default_factory=lambda: [JudgeMode.HUMAN.value])


@dataclass(frozen=True)
class JudgeProfile(VersionedModel):
    name: str = ""
    mode: str = JudgeMode.HUMAN.value
    rubric_id: str | None = None
    model_provider_id: str | None = None
    model_name: str | None = None
    reviewer_id: str | None = None
    consensus_weight: float = 1.0
    instructions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class JudgeResult(VersionedModel):
    task_id: str = ""
    run_id: str | None = None
    model_name: str = ""
    judge_profile_id: str | None = None
    judge_mode: str = JudgeMode.HUMAN.value
    rubric_id: str | None = None
    scores: dict[str, float] = field(default_factory=dict)
    overall_score: float | None = None
    rationale: str | None = None
    comments: dict[str, str] = field(default_factory=dict)
    confidence: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class JudgeConsensus(VersionedModel):
    task_id: str = ""
    run_id: str | None = None
    model_name: str = ""
    strategy: str = ConsensusStrategy.NONE.value
    judge_result_ids: list[str] = field(default_factory=list)
    consensus_score: float | None = None
    agreement_score: float | None = None
    rationale: str | None = None
    unresolved_disagreements: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class JudgePipeline(VersionedModel):
    name: str = ""
    judge_profile_ids: list[str] = field(default_factory=list)
    rubric_id: str | None = None
    consensus_strategy: str = ConsensusStrategy.NONE.value
    supported_modes: list[str] = field(
        default_factory=lambda: [
            JudgeMode.HUMAN.value,
            JudgeMode.LLM.value,
            JudgeMode.MULTI_JUDGE.value,
            JudgeMode.CONSENSUS.value,
        ]
    )
