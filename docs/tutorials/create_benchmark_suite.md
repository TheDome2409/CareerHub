# Create a Benchmark Suite

OpenLLMBench includes a small SDK for scaffolding benchmark suites.

```powershell
python -m openllmbench create-suite "My Suite" --output-root datasets
```

The command creates:

- `dataset.yaml`
- `tasks/`
- `prompts/`
- `media/`
- `references/`
- `README.md`
- `docs/`
- `tests/`

A benchmark suite will define:

- suite ID
- suite version
- task set version
- prompt set version
- tasks
- capability references
- expected output types

Design recommendation: start from real work samples and keep prompts versioned
separately from tasks.
