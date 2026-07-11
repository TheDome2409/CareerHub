# Providers

Providers connect OpenLLMBench to model runtimes.

A provider should define:

- model discovery
- model metadata
- generation API
- streaming generation API
- health checks
- keep-alive behavior
- shutdown behavior
- timeout behavior
- error handling
- raw provider response preservation
- privacy and locality assumptions

The provider interface is intentionally broad enough to support local and
remote runtimes such as Ollama, LM Studio, vLLM, llama.cpp, OpenAI, Claude,
Gemini and MCP-backed model tools.

## Provider API

Reference methods:

- `generate(request)` returns one complete model response.
- `stream(request)` yields incremental response events.
- `health()` reports whether the provider is reachable.
- `metadata()` returns provider-level metadata and capabilities.
- `models()` returns available model metadata.
- `keep_alive(model_name)` warms or keeps a model loaded when supported.
- `shutdown()` releases provider resources when supported.

`list_models()` is kept as a compatibility alias for the original foundation
interface.

## Reference Provider

Ollama is the first reference provider and lives in
`openllmbench.providers.ollama`. It uses the local Ollama HTTP API and does not
replace the existing CareerHub benchmark client yet.
