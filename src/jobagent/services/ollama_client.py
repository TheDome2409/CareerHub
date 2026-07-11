import json
import logging
import os
import time
from typing import Any

import requests


logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: int = 60,
        default_model: str | None = None,
        session=None,
    ):
        self.base_url = (
            base_url
            or os.getenv("OLLAMA_BASE_URL")
            or "http://localhost:11434"
        ).rstrip("/")
        self.timeout = timeout
        self.default_model = (
            default_model
            or os.getenv("COMPANYHUB_OLLAMA_MODEL")
            or os.getenv("OLLAMA_MODEL")
        )
        self.session = session or requests.Session()
        self.last_model: str | None = None

    def is_available(self) -> bool:
        try:
            self.list_models()
        except requests.Timeout:
            logger.warning("Ollama availability check timed out.")
            return False
        except requests.RequestException as exc:
            logger.warning("Ollama availability check failed: %s", exc)
            return False
        except Exception as exc:
            logger.warning("Ollama availability check failed: %s", exc)
            return False

        return True

    def list_models(self) -> list[str]:
        response = self.session.get(
            f"{self.base_url}/api/tags",
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json() or {}

        models = payload.get("models", [])

        return [
            str(model.get("name"))
            for model in models
            if isinstance(model, dict) and str(model.get("name", "")).strip()
        ]

    def _resolve_model(self, model: str | None = None) -> str:
        selected = model or self.default_model

        if selected:
            return selected

        models = self.list_models()

        if models:
            return models[0]

        raise RuntimeError("No Ollama model configured or available.")

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        selected_model = self._resolve_model(model)
        self.last_model = selected_model
        prompt_size = len(system_prompt or "") + len(user_prompt or "")
        started = time.perf_counter()

        logger.info(
            "Calling Ollama model=%s prompt_size=%s",
            selected_model,
            prompt_size,
        )

        try:
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": selected_model,
                    "system": system_prompt,
                    "prompt": user_prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": temperature,
                    },
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.Timeout:
            logger.warning("Ollama request timed out.")
            raise
        except requests.RequestException as exc:
            logger.warning("Ollama request failed: %s", exc)
            raise

        payload = response.json() or {}
        answer = str(payload.get("response", "")).strip()
        duration_ms = int((time.perf_counter() - started) * 1000)

        logger.info(
            "Ollama response model=%s answer_size=%s duration_ms=%s",
            selected_model,
            len(answer),
            duration_ms,
        )

        try:
            return json.loads(answer)
        except json.JSONDecodeError as exc:
            logger.warning("Ollama returned invalid JSON: %s", exc)
            raise ValueError("Ollama returned invalid JSON.") from exc
