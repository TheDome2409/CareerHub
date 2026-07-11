from openllmbench.core.interfaces import Judge, JudgeConsensusProvider, JudgePipelineProvider
from openllmbench.core.models import BenchmarkTask, GenerateRequest, GenerateResult, Prompt
from openllmbench.judges.models import (
    ConsensusStrategy,
    JudgeConsensus,
    JudgeCriterion,
    JudgeMode,
    JudgePipeline,
    JudgeProfile,
    JudgeResult,
    JudgeRubric,
)


class DummyJudge:
    id = "dummy_judge"
    version = "1.0"

    def judge(self, task, result):
        return JudgeResult(
            id="judge_result",
            version="1.0",
            task_id=task.id,
            model_name=result.request.model_name,
            judge_profile_id="human_reviewer",
            judge_mode=JudgeMode.HUMAN.value,
            overall_score=8.0,
        )


class DummyConsensusProvider:
    id = "dummy_consensus"
    version = "1.0"

    def build_consensus(self, results, profile):
        return JudgeConsensus(
            id="consensus",
            version="1.0",
            task_id=results[0].task_id,
            strategy=ConsensusStrategy.AVERAGE.value,
            judge_result_ids=[result.id for result in results],
        )


class DummyPipelineProvider:
    id = "dummy_pipeline"
    version = "1.0"

    def load_pipeline(self, pipeline_id):
        return JudgePipeline(id=pipeline_id, version="1.0")

    def load_rubric(self, rubric_id):
        return JudgeRubric(id=rubric_id, version="1.0")


def _generate_result():
    prompt = Prompt(
        task_id="task",
        prompt_template_id="template",
        prompt_version_id="v1",
        text="Prompt",
    )
    request = GenerateRequest(model_name="model", prompt=prompt)
    return GenerateResult(request=request, response_text="response")


def test_judge_framework_models_support_human_llm_multi_and_consensus():
    rubric = JudgeRubric(
        id="careerhub_rubric",
        version="1.0",
        name="CareerHub Rubric",
        criteria=[
            JudgeCriterion(id="factual_correctness", version="1.0", label="Factual Correctness"),
            JudgeCriterion(id="structure", version="1.0", label="Structure", weight=0.5),
        ],
        supported_modes=[JudgeMode.HUMAN.value, JudgeMode.LLM.value],
    )
    human_profile = JudgeProfile(
        id="human_reviewer",
        version="1.0",
        name="Human Reviewer",
        mode=JudgeMode.HUMAN.value,
        rubric_id=rubric.id,
    )
    llm_profile = JudgeProfile(
        id="llm_reviewer",
        version="1.0",
        name="LLM Reviewer",
        mode=JudgeMode.LLM.value,
        rubric_id=rubric.id,
        model_provider_id="ollama",
        model_name="qwen3:30b",
    )
    pipeline = JudgePipeline(
        id="human_llm_consensus",
        version="1.0",
        name="Human + LLM Consensus",
        judge_profile_ids=[human_profile.id, llm_profile.id],
        rubric_id=rubric.id,
        consensus_strategy=ConsensusStrategy.WEIGHTED_AVERAGE.value,
    )

    assert rubric.criteria[0].scale_min == 0.0
    assert human_profile.mode == "human"
    assert llm_profile.model_provider_id == "ollama"
    assert JudgeMode.MULTI_JUDGE.value in pipeline.supported_modes
    assert pipeline.consensus_strategy == "weighted_average"


def test_judge_interfaces_accept_structural_implementations():
    assert isinstance(DummyJudge(), Judge)
    assert isinstance(DummyConsensusProvider(), JudgeConsensusProvider)
    assert isinstance(DummyPipelineProvider(), JudgePipelineProvider)


def test_judge_result_links_task_model_profile_and_scores():
    task = BenchmarkTask(id="task", version="1.0", title="Task")
    result = DummyJudge().judge(task, _generate_result())

    assert result.task_id == "task"
    assert result.model_name == "model"
    assert result.judge_profile_id == "human_reviewer"
    assert result.overall_score == 8.0


def test_consensus_model_tracks_multiple_judge_results():
    result_a = JudgeResult(id="a", version="1.0", task_id="task", overall_score=8.0)
    result_b = JudgeResult(id="b", version="1.0", task_id="task", overall_score=7.0)
    profile = JudgeProfile(id="profile", version="1.0", mode=JudgeMode.CONSENSUS.value)

    consensus = DummyConsensusProvider().build_consensus([result_a, result_b], profile)

    assert consensus.judge_result_ids == ["a", "b"]
    assert consensus.strategy == "average"
