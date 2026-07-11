import json

from openllmbench.core.interfaces import ModelProvider
from openllmbench.core.models import GenerateRequest, Prompt
from openllmbench.providers.ollama import OllamaProvider


class FakeResponse:
    def __init__(self, payload=None, lines=None):
        self.payload = payload or {}
        self.lines = lines or []

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload

    def iter_lines(self):
        for line in self.lines:
            yield json.dumps(line).encode("utf-8")


def _request(settings=None):
    return GenerateRequest(
        model_name="qwen3:30b",
        prompt=Prompt(
            task_id="task",
            prompt_template_id="template",
            prompt_version_id="v1",
            text="Hello model",
        ),
        settings=settings or {"temperature": 0.2, "top_p": 0.9, "keep_alive": "30m"},
    )


def test_ollama_provider_implements_model_provider_protocol():
    assert isinstance(OllamaProvider(), ModelProvider)


def test_ollama_provider_health_and_metadata(monkeypatch):
    def fake_get(url, timeout):
        assert url.endswith("/api/version")
        return FakeResponse({"version": "0.9.0"})

    monkeypatch.setattr("openllmbench.providers.ollama.requests.get", fake_get)

    provider = OllamaProvider(base_url="http://ollama.test")
    health = provider.health()
    metadata = provider.metadata()

    assert health.available is True
    assert metadata.version == "0.9.0"
    assert metadata.base_url == "http://ollama.test"
    assert "generate" in metadata.capabilities


def test_ollama_provider_models_maps_ollama_tags(monkeypatch):
    def fake_get(url, timeout):
        assert url.endswith("/api/tags")
        return FakeResponse(
            {
                "models": [
                    {
                        "name": "qwen3:30b",
                        "digest": "abc123",
                        "details": {"parameter_size": "30B"},
                    }
                ]
            }
        )

    monkeypatch.setattr("openllmbench.providers.ollama.requests.get", fake_get)

    provider = OllamaProvider()
    models = provider.models()
    legacy_models = provider.list_models()

    assert models[0].name == "qwen3:30b"
    assert models[0].tag == "30b"
    assert models[0].digest == "abc123"
    assert legacy_models[0].provider_id == "ollama"


def test_ollama_provider_generate_passes_keep_alive_and_options(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout, stream=False):
        captured["url"] = url
        captured["json"] = json
        captured["stream"] = stream
        return FakeResponse({"response": "Generated text", "done": True})

    monkeypatch.setattr("openllmbench.providers.ollama.requests.post", fake_post)

    result = OllamaProvider(base_url="http://ollama.test").generate(_request())

    assert result.error is None
    assert result.response_text == "Generated text"
    assert captured["json"]["prompt"] == "Hello model"
    assert captured["json"]["keep_alive"] == "30m"
    assert captured["json"]["options"]["temperature"] == 0.2
    assert captured["stream"] is False


def test_ollama_provider_stream_yields_events(monkeypatch):
    def fake_post(url, json, timeout, stream=False):
        assert stream is True
        return FakeResponse(
            lines=[
                {"response": "Hel", "done": False},
                {"response": "lo", "done": True},
            ]
        )

    monkeypatch.setattr("openllmbench.providers.ollama.requests.post", fake_post)

    events = list(OllamaProvider().stream(_request()))

    assert [event.text for event in events] == ["Hel", "lo"]
    assert events[-1].done is True


def test_ollama_provider_keep_alive_uses_generate_endpoint(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse({"done": True})

    monkeypatch.setattr("openllmbench.providers.ollama.requests.post", fake_post)

    result = OllamaProvider(default_keep_alive="45m").keep_alive("qwen3:30b")

    assert result.success is True
    assert captured["url"].endswith("/api/generate")
    assert captured["json"]["model"] == "qwen3:30b"
    assert captured["json"]["keep_alive"] == "45m"


def test_ollama_provider_shutdown_is_explicit_noop():
    result = OllamaProvider().shutdown()

    assert result.success is True
    assert "no provider-level shutdown" in (result.message or "")
