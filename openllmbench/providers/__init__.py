"""Model provider plugin interfaces and reference providers."""

__all__ = ["OllamaProvider"]


def __getattr__(name: str):
    if name == "OllamaProvider":
        from openllmbench.providers.ollama import OllamaProvider

        return OllamaProvider
    raise AttributeError(name)
