# Benchmark Pipeline

The target OpenLLMBench pipeline is:

```text
Task
↓
PromptBuilder
↓
Prompt
↓
Provider
↓
Model
↓
Telemetry
↓
Archive
↓
Evaluation
↓
Judge
↓
Reporter
↓
Output
```

## Judge Framework Foundation

The judge layer is intentionally split into architecture pieces before any
judging logic is implemented:

- `Judge` represents one reviewer or judging backend.
- `JudgeProfile` describes who or what is judging, such as a human reviewer,
  an LLM reviewer or a future external judge.
- `JudgeRubric` describes criteria and scoring scales.
- `JudgeResult` stores one judging result.
- `JudgeConsensus` represents agreement across multiple judge results.
- `JudgePipeline` describes how human, LLM, multi-judge and consensus workflows
  can be combined later.

The foundation does not evaluate outputs by itself. It only defines the shape
needed for future human review, LLM review, multi-judge and consensus workflows.

## Task

A task describes intent: category, title, expected output type, evaluation hints
and required capabilities. It does not contain the final prompt text.

## PromptBuilder

The prompt builder combines a task, prompt template and prompt version into a
concrete prompt. This allows prompt iteration without rewriting task identity.

## Provider and Model

The provider sends prompts to a model backend. Ollama is the first planned
provider. Other providers can follow the same interface.

## Telemetry

Telemetry records system health, token metrics, timings and other technical
context. Telemetry must not judge output quality.

## Archive

Archive backends index results for later comparison. DuckDB is the first planned
archive backend.

## Evaluation and Judge

Evaluators are deterministic or rules-based. Judges can be human or LLM-based
and should remain optional.

## Reporter

Reporters render summaries, CSV exports, dashboards or other views. Raw JSON
artifacts remain the primary record of a run.
