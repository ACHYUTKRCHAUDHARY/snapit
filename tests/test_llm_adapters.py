import httpx
import pytest
from pydantic import SecretStr

from snappe.adapters.llm import (
    FakeLLMClient,
    GeminiLLMClient,
    create_llm_client,
)
from snappe.application.brain import LLMUnavailable
from snappe.config import Settings


def test_fake_llm_client_default_and_keyword_responses() -> None:
    client = FakeLLMClient(
        default_response="Default text",
        responses={"hours": '{"reply": "9 to 5"}'},
    )

    resp1 = client.generate("system", "User asks about hours")
    resp2 = client.generate("system", "User asks about location")

    assert resp1 == '{"reply": "9 to 5"}'
    assert resp2 == "Default text"
    assert len(client.history) == 2


def test_fake_llm_client_raises_configured_error() -> None:
    client = FakeLLMClient(raise_error=TimeoutError("Timed out"))

    with pytest.raises(TimeoutError, match="Timed out"):
        client.generate("sys", "usr")


def test_gemini_client_success() -> None:
    expected_reply = '{"reply": "Open 9-5", "cited_fact_keys": ["hours"]}'

    def handler(request: httpx.Request) -> httpx.Response:
        assert "key=test-api-key" in str(request.url)
        payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": expected_reply}],
                    }
                }
            ]
        }
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    client = GeminiLLMClient(
        api_key="test-api-key",
        http_client=http_client,
    )

    result = client.generate("System instruction", "User prompt")
    assert result == expected_reply


def test_gemini_client_handles_http_errors() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Service Unavailable")

    transport = httpx.MockTransport(handler)
    client = GeminiLLMClient(
        api_key="test-api-key",
        http_client=httpx.Client(transport=transport),
    )

    with pytest.raises(LLMUnavailable, match="503"):
        client.generate("sys", "usr")


def test_gemini_client_handles_network_timeout() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("Connection timed out")

    transport = httpx.MockTransport(handler)
    client = GeminiLLMClient(
        api_key="test-api-key",
        http_client=httpx.Client(transport=transport),
    )

    with pytest.raises(LLMUnavailable, match="network error"):
        client.generate("sys", "usr")


def test_gemini_client_handles_empty_candidates() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"candidates": []})

    transport = httpx.MockTransport(handler)
    client = GeminiLLMClient(
        api_key="test-api-key",
        http_client=httpx.Client(transport=transport),
    )

    with pytest.raises(LLMUnavailable, match="no candidates"):
        client.generate("sys", "usr")


def test_gemini_client_handles_malformed_candidate() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": 123}]}}]})

    transport = httpx.MockTransport(handler)
    client = GeminiLLMClient(
        api_key="test-api-key",
        http_client=httpx.Client(transport=transport),
    )

    with pytest.raises(LLMUnavailable, match="missing or invalid"):
        client.generate("sys", "usr")


def test_create_llm_client_factory() -> None:
    fake_settings = Settings(_env_file=None, llm_provider="fake")
    assert isinstance(create_llm_client(fake_settings), FakeLLMClient)

    gemini_no_key = Settings(_env_file=None, llm_provider="gemini")
    assert isinstance(create_llm_client(gemini_no_key), FakeLLMClient)

    gemini_with_key = Settings(
        _env_file=None,
        llm_provider="gemini",
        gemini_api_key=SecretStr("gemini-test-secret"),
    )
    assert isinstance(create_llm_client(gemini_with_key), GeminiLLMClient)
