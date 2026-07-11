import json

import pytest
import requests

from jobagent.services.ollama_client import OllamaClient


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self.payload = payload or {}
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, get_response=None, post_response=None, get_exc=None, post_exc=None):
        self.get_response = get_response
        self.post_response = post_response
        self.get_exc = get_exc
        self.post_exc = post_exc
        self.get_calls = []
        self.post_calls = []

    def get(self, url, timeout):
        self.get_calls.append(
            {
                "url": url,
                "timeout": timeout,
            }
        )
        if self.get_exc:
            raise self.get_exc

        return self.get_response or FakeResponse()

    def post(self, url, json, timeout):
        self.post_calls.append(
            {
                "url": url,
                "json": json,
                "timeout": timeout,
            }
        )
        if self.post_exc:
            raise self.post_exc

        return self.post_response or FakeResponse()


def test_list_models_reads_ollama_tags():
    session = FakeSession(
        get_response=FakeResponse(
            {
                "models": [
                    {
                        "name": "qwen-test:14b",
                    }
                ]
            }
        )
    )
    client = OllamaClient(
        session=session,
        timeout=7,
    )

    assert client.list_models() == [
        "qwen-test:14b",
    ]
    assert session.get_calls[0]["url"] == "http://localhost:11434/api/tags"
    assert session.get_calls[0]["timeout"] == 7


def test_is_available_returns_false_on_connection_error():
    client = OllamaClient(
        session=FakeSession(
            get_exc=requests.ConnectionError("refused")
        )
    )

    assert client.is_available() is False


def test_generate_json_uses_json_mode_and_selected_model():
    session = FakeSession(
        post_response=FakeResponse(
            {
                "response": json.dumps(
                    {
                        "mission": "Digitale Infrastruktur",
                    }
                )
            }
        )
    )
    client = OllamaClient(
        session=session,
        default_model="qwen-test:32b",
    )

    result = client.generate_json(
        "System",
        "User",
        temperature=0.2,
    )

    request_payload = session.post_calls[0]["json"]
    assert result == {
        "mission": "Digitale Infrastruktur",
    }
    assert request_payload["model"] == "qwen-test:32b"
    assert request_payload["format"] == "json"
    assert request_payload["stream"] is False
    assert request_payload["options"]["temperature"] == 0.2
    assert client.last_model == "qwen-test:32b"


def test_generate_json_falls_back_to_first_listed_model():
    session = FakeSession(
        get_response=FakeResponse(
            {
                "models": [
                    {
                        "name": "qwen-auto:14b",
                    }
                ]
            }
        ),
        post_response=FakeResponse(
            {
                "response": "{}",
            }
        ),
    )
    client = OllamaClient(
        session=session,
    )

    assert client.generate_json("System", "User") == {}
    assert session.post_calls[0]["json"]["model"] == "qwen-auto:14b"


def test_generate_json_rejects_invalid_json():
    client = OllamaClient(
        session=FakeSession(
            post_response=FakeResponse(
                {
                    "response": "not json",
                }
            )
        ),
        default_model="qwen-test:14b",
    )

    with pytest.raises(ValueError):
        client.generate_json("System", "User")


def test_generate_json_propagates_timeout_for_reviewer_fallback():
    client = OllamaClient(
        session=FakeSession(
            post_exc=requests.Timeout("slow")
        ),
        default_model="qwen-test:14b",
    )

    with pytest.raises(requests.Timeout):
        client.generate_json("System", "User")
