from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import openai
from openai import OpenAI

from app.config import OpenAISettings


class AIProviderError(RuntimeError):
    """Safe provider error without credentials or upstream response details."""


class AIProviderUnavailableError(AIProviderError):
    pass


class AIProviderTimeoutError(AIProviderError):
    pass


class AIProviderAuthenticationError(AIProviderError):
    pass


class AIProviderRateLimitError(AIProviderError):
    pass


class AIProviderServerError(AIProviderError):
    pass


class AIProviderOutputError(AIProviderError):
    pass


@dataclass(frozen=True)
class AIExplanation:
    text: str
    model: str


class AIProvider(Protocol):
    def explain(self, *, instructions: str, input_text: str) -> AIExplanation: ...


class OpenAIProvider:
    def __init__(self, settings: OpenAISettings) -> None:
        self._settings = settings
        self._client: OpenAI | None = None

    @property
    def model(self) -> str:
        return self._settings.model

    def explain(self, *, instructions: str, input_text: str) -> AIExplanation:
        if not self._settings.api_key:
            raise AIProviderUnavailableError("OPENAI_API_KEY is not configured")

        try:
            response = self._get_client().responses.create(
                model=self._settings.model,
                instructions=instructions,
                input=input_text,
                reasoning={"effort": "low"},
                max_output_tokens=500,
                store=False,
            )
        except openai.APITimeoutError as exc:
            raise AIProviderTimeoutError("OpenAI request timed out") from exc
        except openai.AuthenticationError as exc:
            raise AIProviderAuthenticationError(
                "OpenAI authentication failed"
            ) from exc
        except openai.RateLimitError as exc:
            raise AIProviderRateLimitError("OpenAI rate limit reached") from exc
        except (openai.InternalServerError, openai.APIConnectionError) as exc:
            raise AIProviderServerError("OpenAI provider unavailable") from exc
        except openai.APIStatusError as exc:
            raise AIProviderServerError("OpenAI provider request failed") from exc
        except openai.OpenAIError as exc:
            raise AIProviderServerError("OpenAI provider request failed") from exc

        output_text = (getattr(response, "output_text", None) or "").strip()
        if not output_text:
            raise AIProviderOutputError("OpenAI returned empty output")
        response_model = getattr(response, "model", None) or self._settings.model
        return AIExplanation(text=output_text, model=response_model)

    def _get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=self._settings.api_key,
                timeout=self._settings.timeout_seconds,
                max_retries=0,
            )
        return self._client
