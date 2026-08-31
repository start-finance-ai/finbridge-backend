from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import openai
from openai import OpenAI

from app.config import OpenAISettings


class AIProviderError(RuntimeError):
    """Safe provider error without credentials or upstream response details."""

    reason_code = "PROVIDER_ERROR"


class AIProviderUnavailableError(AIProviderError):
    reason_code = "CONFIG_UNAVAILABLE"


class AIProviderTimeoutError(AIProviderError):
    reason_code = "TIMEOUT"


class AIProviderAuthenticationError(AIProviderError):
    reason_code = "AUTHENTICATION"


class AIProviderRateLimitError(AIProviderError):
    reason_code = "RATE_LIMIT"


class AIProviderQuotaError(AIProviderError):
    reason_code = "QUOTA"


class AIProviderServerError(AIProviderError):
    reason_code = "SERVER"


class AIProviderRequestError(AIProviderError):
    reason_code = "REQUEST"


class AIProviderOutputError(AIProviderError):
    reason_code = "EMPTY_OR_INVALID_OUTPUT"


class AIProviderIncompleteError(AIProviderOutputError):
    reason_code = "INCOMPLETE_OUTPUT"


class AIProviderMaxOutputTokensError(AIProviderIncompleteError):
    reason_code = "MAX_OUTPUT_TOKENS"


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

        response = self._create_response(
            instructions=instructions,
            input_text=input_text,
        )

        status = getattr(response, "status", None)
        if status == "incomplete":
            details = getattr(response, "incomplete_details", None)
            reason = (
                details.get("reason")
                if isinstance(details, dict)
                else getattr(details, "reason", None)
            )
            if reason == "max_output_tokens":
                raise AIProviderMaxOutputTokensError(
                    "OpenAI response reached max_output_tokens"
                )
            raise AIProviderIncompleteError("OpenAI response was incomplete")
        if status in {"failed", "cancelled", "in_progress", "queued"}:
            raise AIProviderOutputError(
                f"OpenAI response status was not completed: {status}"
            )

        output_text = (getattr(response, "output_text", None) or "").strip()
        if not output_text:
            raise AIProviderOutputError("OpenAI returned empty output")
        response_model = getattr(response, "model", None) or self._settings.model
        return AIExplanation(text=output_text, model=response_model)

    def _create_response(self, *, instructions: str, input_text: str):
        for attempt in range(2):
            try:
                return self._get_client().responses.create(
                    model=self._settings.model,
                    instructions=instructions,
                    input=input_text,
                    reasoning={"effort": "low"},
                    max_output_tokens=self._settings.max_output_tokens,
                    store=False,
                )
            except openai.APITimeoutError as exc:
                if attempt == 0:
                    continue
                raise AIProviderTimeoutError("OpenAI request timed out") from exc
            except openai.AuthenticationError as exc:
                raise AIProviderAuthenticationError(
                    "OpenAI authentication failed"
                ) from exc
            except openai.RateLimitError as exc:
                if _is_quota_error(exc):
                    raise AIProviderQuotaError("OpenAI quota unavailable") from exc
                if attempt == 0:
                    continue
                raise AIProviderRateLimitError("OpenAI rate limit reached") from exc
            except (openai.InternalServerError, openai.APIConnectionError) as exc:
                if attempt == 0:
                    continue
                raise AIProviderServerError(
                    "OpenAI provider unavailable"
                ) from exc
            except openai.APIStatusError as exc:
                if exc.status_code in {408, 409} and attempt == 0:
                    continue
                raise AIProviderRequestError(
                    "OpenAI provider request failed"
                ) from exc
            except openai.OpenAIError as exc:
                raise AIProviderRequestError(
                    "OpenAI provider request failed"
                ) from exc
        raise AIProviderServerError("OpenAI provider unavailable")

    def _get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=self._settings.api_key,
                timeout=self._settings.timeout_seconds,
                max_retries=0,
            )
        return self._client


def _is_quota_error(exc: openai.RateLimitError) -> bool:
    body = getattr(exc, "body", None)
    if not isinstance(body, dict):
        return False
    error = body.get("error") if isinstance(body.get("error"), dict) else body
    return error.get("code") == "insufficient_quota" or error.get(
        "type"
    ) == "insufficient_quota"
