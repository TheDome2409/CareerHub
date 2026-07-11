from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

import requests

from openllmbench.core.models import GenerateRequest, GenerateResult, ModelInfo
from openllmbench.providers.models import (
    ProviderHealth,
    ProviderKeepAliveResult,
    ProviderMetadata,
    ProviderModelInfo,
    ProviderShutdownResult,
    ProviderStreamEvent,
)


class OllamaProvider:
    id = "ollama"
    version = "1.0"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout_seconds: int = 600,
        default_keep_alive: str = "30m",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.default_keep_alive = default_keep_alive

    def generate(self, request: GenerateRequest) -> GenerateResult:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=self._build_generate_payload(request, stream=False),
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            return GenerateResult(
                request=request,
                response_text=str(payload.get("response") or ""),
                raw=payload,
            )
        except Exception as exc:
            return GenerateResult(
                request=request,
                response_text="",
                raw={},
                error=str(exc),
            )

    def stream(self, request: GenerateRequest) -> Iterable[ProviderStreamEvent]:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=self._build_generate_payload(request, stream=True),
                timeout=self.timeout_seconds,
                stream=True,
            )
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    payload = json.loads(line.decode("utf-8"))
                except Exception as exc:
                    yield ProviderStreamEvent(done=True, error=str(exc), raw={"line": str(line)})
                    continue
                yield ProviderStreamEvent(
                    text=str(payload.get("response") or ""),
                    done=bool(payload.get("done")),
                    raw=payload,
                )
        except Exception as exc:
            yield ProviderStreamEvent(done=True, error=str(exc))

    def health(self) -> ProviderHealth:
        try:
            response = requests.get(f"{self.base_url}/api/version", timeout=10)
            response.raise_for_status()
            payload = response.json()
            return ProviderHealth(
                provider_id=self.id,
                available=True,
                status="available",
                message="Ollama is reachable.",
                metadata=payload,
            )
        except Exception as exc:
            return ProviderHealth(
                provider_id=self.id,
                available=False,
                status="unavailable",
                message=str(exc),
            )

    def metadata(self) -> ProviderMetadata:
        health = self.health()
        return ProviderMetadata(
            provider_id=self.id,
            name="Ollama",
            version=str(health.metadata.get("version")) if health.metadata.get("version") else None,
            base_url=self.base_url,
            capabilities=["generate", "stream", "models", "keep_alive", "local"],
            raw=health.metadata,
        )

    def models(self) -> list[ProviderModelInfo]:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=30)
            response.raise_for_status()
            payload = response.json()
            return [self._model_from_ollama(item) for item in payload.get("models", [])]
        except Exception:
            return []

    def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                id=model.name,
                version="1.0",
                provider_id=self.id,
                name=model.name,
                digest=model.digest,
                capability_ids=model.capability_ids,
                metadata=model.details,
            )
            for model in self.models()
        ]

    def keep_alive(self, model_name: str) -> ProviderKeepAliveResult:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": self.default_keep_alive,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            return ProviderKeepAliveResult(
                provider_id=self.id,
                model_name=model_name,
                success=True,
                message="Model keep-alive request completed.",
                raw=payload,
            )
        except Exception as exc:
            return ProviderKeepAliveResult(
                provider_id=self.id,
                model_name=model_name,
                success=False,
                message=str(exc),
            )

    def shutdown(self) -> ProviderShutdownResult:
        return ProviderShutdownResult(
            provider_id=self.id,
            success=True,
            message="Ollama has no provider-level shutdown endpoint; no action was taken.",
        )

    def _build_generate_payload(self, request: GenerateRequest, stream: bool) -> dict[str, Any]:
        settings = dict(request.settings or {})
        keep_alive = settings.pop("keep_alive", self.default_keep_alive)
        options = settings.pop("options", settings)
        return {
            "model": request.model_name,
            "prompt": request.prompt.text,
            "stream": stream,
            "keep_alive": keep_alive,
            "options": options,
        }

    def _model_from_ollama(self, item: dict[str, Any]) -> ProviderModelInfo:
        name = str(item.get("name") or item.get("model") or "")
        return ProviderModelInfo(
            provider_id=self.id,
            name=name,
            tag=name.split(":", 1)[1] if ":" in name else None,
            digest=item.get("digest"),
            details=item.get("details") or {},
            raw=item,
        )
