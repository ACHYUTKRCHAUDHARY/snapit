"""LLM adapters for Gemini and deterministic test fakes."""

import json
from collections.abc import Mapping
from typing import Any

import httpx

from snappe.application.brain import LLMClient, LLMUnavailable
from snappe.config import Settings

_DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"
_GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
_HTTP_OK = 200


class FakeLLMClient:
    """Deterministic in-memory LLM client for tests and offline development."""

    def __init__(
        self,
        default_response: str | None = None,
        responses: Mapping[str, str] | None = None,
        raise_error: Exception | None = None,
    ) -> None:
        self.default_response = default_response or json.dumps(
            {
                "reply": "Thank you for contacting us.",
                "cited_fact_keys": [],
                "intent": "general",
                "requires_handover": False,
            }
        )
        self.responses = dict(responses or {})
        self.raise_error = raise_error
        self.history: list[tuple[str, str]] = []

    def generate(self, system_instruction: str, user_prompt: str) -> str:
        self.history.append((system_instruction, user_prompt))
        if self.raise_error is not None:
            raise self.raise_error

        for keyword, response in self.responses.items():
            if keyword in user_prompt:
                return response

        return self.default_response


class GeminiLLMClient:
    """Google Gemini API client using HTTP REST endpoint."""

    def __init__(
        self,
        api_key: str,
        model: str = _DEFAULT_GEMINI_MODEL,
        timeout_seconds: float = 10.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._client = http_client

    def generate(self, system_instruction: str, user_prompt: str) -> str:
        url = f"{_GEMINI_API_ENDPOINT}/{self._model}:generateContent"
        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }

        try:
            client = self._client or httpx.Client(timeout=self._timeout)
            try:
                response = client.post(
                    url,
                    params={"key": self._api_key},
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
            finally:
                if self._client is None:
                    client.close()
        except (httpx.HTTPError, httpx.TimeoutException) as error:
            raise LLMUnavailable(f"Gemini API network error: {error}") from error

        if response.status_code != _HTTP_OK:
            raise LLMUnavailable(
                f"Gemini API returned status {response.status_code}: {response.text}"
            )

        try:
            data: Mapping[str, Any] = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise LLMUnavailable("Gemini API returned no candidates")
            text = candidates[0]["content"]["parts"][0]["text"]
            if not isinstance(text, str):
                raise LLMUnavailable("Gemini API candidate text is missing or invalid")
            return text
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise LLMUnavailable(f"Gemini API response structure invalid: {error}") from error


def create_llm_client(settings: Settings) -> LLMClient:
    """Instantiate the configured LLM client provider."""
    if settings.llm_provider.lower() == "gemini" and settings.gemini_api_key is not None:
        return GeminiLLMClient(
            api_key=settings.gemini_api_key.get_secret_value(),
            model=settings.llm_model or _DEFAULT_GEMINI_MODEL,
        )
    return FakeLLMClient()
