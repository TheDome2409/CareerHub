from __future__ import annotations

from dataclasses import dataclass
import logging
from time import perf_counter
from typing import Any

import requests


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OllamaGenerateResult:
    response: str
    duration_seconds: float
    error: str | None
    raw: dict[str, Any]


class OllamaGenerateClient:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout_seconds: int = 600,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def generate(
        self,
        *,
        model: str,
        prompt: str,
        keep_alive: str = "30m",
        options: dict[str, Any] | None = None,
    ) -> OllamaGenerateResult:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": keep_alive,
            "options": options or {},
        }
        started = perf_counter()
        try:
            logger.info("Running Ollama generate: model=%s keep_alive=%s", model, keep_alive)
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout_seconds,
            )
            duration = perf_counter() - started
            response.raise_for_status()
            data = response.json()
            logger.info(
                "Ollama generate finished: model=%s duration=%.2fs response_chars=%s",
                model,
                duration,
                len(str(data.get("response", ""))),
            )
            return OllamaGenerateResult(
                response=str(data.get("response", "")),
                duration_seconds=duration,
                error=None,
                raw=data,
            )
        except Exception as exc:  # pragma: no cover - exact requests errors vary.
            duration = perf_counter() - started
            logger.warning(
                "Ollama generate failed: model=%s duration=%.2fs error=%s",
                model,
                duration,
                exc,
            )
            return OllamaGenerateResult(
                response="",
                duration_seconds=duration,
                error=str(exc),
                raw={},
            )

    def list_models(self) -> list[dict[str, Any]]:
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=min(self.timeout_seconds, 30),
            )
            response.raise_for_status()
            data = response.json()
            return list(data.get("models", []) or [])
        except Exception as exc:
            logger.warning("Could not load Ollama model metadata: %s", exc)
            return []

    def get_model_metadata(self, model_name: str) -> dict[str, Any]:
        for model in self.list_models():
            if model.get("name") == model_name or model.get("model") == model_name:
                show_data = self.show_model(model_name)
                details = show_data.get("details") or model.get("details") or {}
                raw = {**model, "show": show_data} if show_data else model
                return {
                    "name": model.get("name") or model.get("model") or model_name,
                    "tag": _model_tag(model_name),
                    "digest": model.get("digest"),
                    "details": details,
                    "model_info": show_data.get("model_info") or {},
                    "capabilities": show_data.get("capabilities"),
                    "parameters": show_data.get("parameters"),
                    "raw": raw,
                }
        return {
            "name": model_name,
            "tag": _model_tag(model_name),
            "digest": None,
            "details": {},
            "model_info": {},
            "capabilities": None,
            "parameters": None,
            "raw": {},
        }

    def show_model(self, model_name: str) -> dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"model": model_name},
                timeout=min(self.timeout_seconds, 60),
            )
            response.raise_for_status()
            return dict(response.json() or {})
        except Exception as exc:
            logger.warning("Could not load Ollama show metadata for %s: %s", model_name, exc)
            return {}

    def get_ollama_version(self) -> str | None:
        try:
            response = requests.get(
                f"{self.base_url}/api/version",
                timeout=min(self.timeout_seconds, 30),
            )
            response.raise_for_status()
            data = response.json()
            version = data.get("version")
            return str(version) if version else None
        except Exception as exc:
            logger.warning("Could not load Ollama version: %s", exc)
            return None


def _model_tag(model_name: str) -> str | None:
    if ":" not in model_name:
        return None
    return model_name.rsplit(":", 1)[-1]
