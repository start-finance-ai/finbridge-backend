from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.ai.provider import (
    AIExplanation,
    AIProviderAuthenticationError,
    AIProviderRateLimitError,
    AIProviderServerError,
    AIProviderTimeoutError,
    OpenAIProvider,
)
from app.config import OpenAISettings, get_openai_settings
from app.main import create_app
from tests.conftest import ASGITestClient


SUPPORTED_PROGRAM_ID = "PBLN_000000000125612"
REVIEW_PROGRAM_ID = "PBLN_000000000125864"


class SuccessfulProvider:
    def __init__(self, text: str = "구조화된 결과를 바탕으로 안내드립니다.") -> None:
        self.text = text
        self.calls: list[dict[str, str]] = []

    def explain(self, *, instructions: str, input_text: str) -> AIExplanation:
        self.calls.append({"instructions": instructions, "input_text": input_text})
        return AIExplanation(text=self.text, model="test-model")


class FailingProvider:
    def __init__(self, error):
        self.error = error

    def explain(self, *, instructions: str, input_text: str) -> AIExplanation:
        del instructions, input_text
        raise self.error


def client_for(provider, monkeypatch, snapshot_path) -> ASGITestClient:
    monkeypatch.setenv("FINBRIDGE_BIZINFO_SNAPSHOT", str(snapshot_path))
    return ASGITestClient(create_app(ai_provider=provider))


def test_chat_defaults_to_general_mode(monkeypatch, snapshot_path) -> None:
    client = client_for(SuccessfulProvider(), monkeypatch, snapshot_path)

    response = client.post("/chat", json={"message": "안녕하세요"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "GENERAL"
    assert payload["reply_source"] == "LLM"
    assert payload["reply"]
    assert payload["programs"] == []
    assert payload["matches"] == []


def test_general_mode_suggests_focus_without_profile(
    monkeypatch, snapshot_path
) -> None:
    client = client_for(SuccessfulProvider(), monkeypatch, snapshot_path)

    response = client.post("/chat", json={"message": "지원사업을 찾아주세요"})

    assert response.json()["suggest_focus_mode"] is True


def test_focus_mode_preserves_profile_in_minimal_prompt(
    monkeypatch, snapshot_path
) -> None:
    provider = SuccessfulProvider()
    client = client_for(provider, monkeypatch, snapshot_path)

    response = client.post(
        "/chat",
        json={
            "mode": "FOCUS",
            "message": "제 조건을 확인해 주세요",
            "focus_profile": {
                "user_type": "PRE_FOUNDER",
                "region": "동구",
                "age": 30,
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "FOCUS"
    assert response.json()["suggest_focus_mode"] is False
    assert '"region":"동구"' in provider.calls[0]["input_text"]
    assert '"raw_source"' not in provider.calls[0]["input_text"]


def test_valid_program_context_preserves_program_evidence_and_source(
    monkeypatch, snapshot_path
) -> None:
    client = client_for(SuccessfulProvider(), monkeypatch, snapshot_path)

    response = client.post(
        "/chat",
        json={"message": "이 공고를 설명해 주세요", "program_id": SUPPORTED_PROGRAM_ID},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["program_context_id"] == SUPPORTED_PROGRAM_ID
    assert payload["programs"][0]["program_id"] == SUPPORTED_PROGRAM_ID
    assert len(payload["evidence"]) == 3
    assert all(item["source_field"] for item in payload["evidence"])
    assert payload["sources"][0]["source"] == "BIZINFO"
    assert payload["sources"][0]["source_url"]
    assert payload["actions"]


def test_invalid_program_context_returns_404(monkeypatch, snapshot_path) -> None:
    client = client_for(SuccessfulProvider(), monkeypatch, snapshot_path)

    response = client.post(
        "/chat",
        json={"message": "없는 공고", "program_id": "PBLN_NOT_FOUND"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "PROGRAM_NOT_FOUND"


def test_program_and_profile_reuse_deterministic_matcher(
    monkeypatch, snapshot_path
) -> None:
    client = client_for(SuccessfulProvider(), monkeypatch, snapshot_path)

    response = client.post(
        "/chat",
        json={
            "mode": "FOCUS",
            "message": "제가 대상인지 설명해 주세요",
            "program_id": SUPPORTED_PROGRAM_ID,
            "focus_profile": {
                "region": "동구",
                "business_region": "동구",
                "age": 30,
                "pre_founder": True,
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["matches"][0]["match_status"] == "MATCH"
    assert len(payload["matches"][0]["condition_results"]) == 3
    assert len(payload["evidence"]) == 3
    assert payload["reply"] == "구조화된 결과를 바탕으로 안내드립니다."


def test_needs_review_match_is_preserved_separately_from_llm_reply(
    monkeypatch, snapshot_path
) -> None:
    client = client_for(
        SuccessfulProvider("자연어 설명입니다."), monkeypatch, snapshot_path
    )

    response = client.post(
        "/chat",
        json={
            "message": "이 공고는 어떤가요?",
            "program_id": REVIEW_PROGRAM_ID,
            "focus_profile": {"age": 30, "pre_founder": True},
        },
    )

    payload = response.json()
    assert payload["reply"] == "자연어 설명입니다."
    assert payload["matches"][0]["match_status"] == "NEEDS_REVIEW"
    assert payload["evidence"]


@pytest.mark.parametrize(
    "error",
    [
        AIProviderTimeoutError("timeout"),
        AIProviderAuthenticationError("authentication"),
        AIProviderRateLimitError("rate-limit"),
        AIProviderServerError("server"),
    ],
    ids=["timeout", "authentication", "rate-limit", "server"],
)
def test_provider_failures_return_template_with_structured_results(
    error, monkeypatch, snapshot_path
) -> None:
    client = client_for(FailingProvider(error), monkeypatch, snapshot_path)

    response = client.post(
        "/chat",
        json={
            "message": "제 조건을 확인해 주세요",
            "program_id": SUPPORTED_PROGRAM_ID,
            "focus_profile": {
                "region": "동구",
                "business_region": "동구",
                "age": 30,
                "pre_founder": True,
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["reply_source"] == "TEMPLATE_FALLBACK"
    assert payload["reply"]
    assert payload["matches"][0]["match_status"] == "MATCH"
    assert len(payload["evidence"]) == 3
    assert payload["sources"][0]["source_url"]


def test_empty_provider_output_returns_template_fallback(
    monkeypatch, snapshot_path
) -> None:
    client = client_for(SuccessfulProvider("   "), monkeypatch, snapshot_path)

    response = client.post("/chat", json={"message": "안녕하세요"})

    assert response.status_code == 200
    assert response.json()["reply_source"] == "TEMPLATE_FALLBACK"
    assert response.json()["reply"]


def test_missing_api_key_returns_template_fallback(
    monkeypatch, snapshot_path
) -> None:
    provider = OpenAIProvider(
        OpenAISettings(api_key=None, model="gpt-5.6-luna", timeout_seconds=1)
    )
    client = client_for(provider, monkeypatch, snapshot_path)

    response = client.post("/chat", json={"message": "안녕하세요"})

    assert response.status_code == 200
    assert response.json()["reply_source"] == "TEMPLATE_FALLBACK"
    assert response.json()["model"] is None


def test_openai_provider_uses_responses_api_with_low_reasoning() -> None:
    class FakeResponses:
        def __init__(self) -> None:
            self.kwargs = None

        def create(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(output_text="설명", model="gpt-5.6-luna")

    fake_responses = FakeResponses()
    provider = OpenAIProvider(
        OpenAISettings(api_key="test-key", model="gpt-5.6-luna", timeout_seconds=3)
    )
    provider._client = SimpleNamespace(responses=fake_responses)

    result = provider.explain(instructions="규칙", input_text="문맥")

    assert result.text == "설명"
    assert fake_responses.kwargs["model"] == "gpt-5.6-luna"
    assert fake_responses.kwargs["reasoning"] == {"effort": "low"}
    assert fake_responses.kwargs["max_output_tokens"] == 900
    assert fake_responses.kwargs["store"] is False


def test_openai_settings_environment_override_does_not_expose_key_in_repr(
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "secret-for-test")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", "4.5")
    monkeypatch.setenv("OPENAI_MAX_OUTPUT_TOKENS", "950")

    settings = get_openai_settings()

    assert settings.api_key == "secret-for-test"
    assert settings.model == "test-model"
    assert settings.timeout_seconds == 4.5
    assert settings.max_output_tokens == 950
    assert "secret-for-test" not in repr(settings)


@pytest.mark.parametrize("value", ["invalid", "0", "-1"])
def test_openai_max_output_tokens_invalid_value_uses_default(
    value, monkeypatch
) -> None:
    monkeypatch.setenv("OPENAI_MAX_OUTPUT_TOKENS", value)

    settings = get_openai_settings()

    assert settings.max_output_tokens == 900
