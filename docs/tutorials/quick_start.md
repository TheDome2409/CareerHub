# Quick Start

OpenLLMBench is currently a foundation package. Runtime benchmarks still use
the CareerHub benchmark runner.

Current benchmark command:

```powershell
python -m careerhub.benchmark_runner --config config/benchmark_models.yaml
```

Foundation status command:

```powershell
python -m openllmbench
```

Future command:

```powershell
python -m openllmbench run --suite careerhub --provider ollama
```

