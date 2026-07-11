"""Judge plugin interfaces and foundation models."""

__all__ = [
    "ConsensusStrategy",
    "Judge",
    "JudgeConsensus",
    "JudgeConsensusProvider",
    "JudgeCriterion",
    "JudgeMode",
    "JudgePipeline",
    "JudgePipelineProvider",
    "JudgeProfile",
    "JudgeResult",
    "JudgeRubric",
]


def __getattr__(name: str):
    if name in {"Judge", "JudgeConsensusProvider", "JudgePipelineProvider"}:
        from openllmbench.judges import base

        return getattr(base, name)
    if name in {
        "ConsensusStrategy",
        "JudgeConsensus",
        "JudgeCriterion",
        "JudgeMode",
        "JudgePipeline",
        "JudgeProfile",
        "JudgeResult",
        "JudgeRubric",
    }:
        from openllmbench.judges import models

        return getattr(models, name)
    raise AttributeError(name)
