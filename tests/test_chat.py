from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import openai
import pytest

from app.ai.fallback import build_template_reply
from app.ai.provider import (
    AIExplanation,
    AIProviderAuthenticationError,
    AIProviderMaxOutputTokensError,
    AIProviderQuotaError,
    AIProviderRateLimitError,
    AIProviderServerError,
    AIProviderTimeoutError,
    OpenAIProvider,
)
from app.config import OpenAISettings, get_openai_settings
from app.main import create_app
from app.schemas.matching import MatchStatus
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
    assert fake_responses.kwargs["max_output_tokens"] == 1200
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

    assert settings.max_output_tokens == 1200


@pytest.mark.parametrize("value", ["invalid", "0", "-1"])
def test_openai_timeout_invalid_value_uses_default(value, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", value)

    settings = get_openai_settings()

    assert settings.timeout_seconds == 30.0


def test_incomplete_max_output_tokens_is_not_returned_as_partial_reply(
    monkeypatch, snapshot_path
) -> None:
    class IncompleteResponses:
        def create(self, **kwargs):
            del kwargs
            return SimpleNamespace(
                output_text="접수 기간: 202",
                model="gpt-5.6-luna",
                status="incomplete",
                incomplete_details=SimpleNamespace(reason="max_output_tokens"),
            )

    provider = OpenAIProvider(OpenAISettings(api_key="test-key"))
    provider._client = SimpleNamespace(responses=IncompleteResponses())

    with pytest.raises(AIProviderMaxOutputTokensError):
        provider.explain(instructions="규칙", input_text="문맥")

    client = client_for(provider, monkeypatch, snapshot_path)
    response = client.post(
        "/chat",
        json={"message": "대구에서 창업을 준비 중인데 지원사업을 알려줘"},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["reply_source"] == "TEMPLATE_FALLBACK"
    assert "접수 기간: 202" not in payload["reply"]
    assert "공식 출처" in payload["reply"]
    assert payload["sources"]


def test_transient_timeout_retries_only_once() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")

    class RetryResponses:
        def __init__(self) -> None:
            self.calls = 0

        def create(self, **kwargs):
            del kwargs
            self.calls += 1
            if self.calls == 1:
                raise openai.APITimeoutError(request=request)
            return SimpleNamespace(
                output_text="재시도 성공",
                model="gpt-5.6-luna",
                status="completed",
            )

    responses = RetryResponses()
    provider = OpenAIProvider(OpenAISettings(api_key="test-key"))
    provider._client = SimpleNamespace(responses=responses)

    result = provider.explain(instructions="규칙", input_text="문맥")

    assert result.text == "재시도 성공"
    assert responses.calls == 2


def test_authentication_error_is_not_retried() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    upstream_response = httpx.Response(401, request=request)

    class AuthFailureResponses:
        def __init__(self) -> None:
            self.calls = 0

        def create(self, **kwargs):
            del kwargs
            self.calls += 1
            raise openai.AuthenticationError(
                "authentication failed",
                response=upstream_response,
                body={"error": {"code": "invalid_api_key"}},
            )

    responses = AuthFailureResponses()
    provider = OpenAIProvider(OpenAISettings(api_key="test-key"))
    provider._client = SimpleNamespace(responses=responses)

    with pytest.raises(AIProviderAuthenticationError):
        provider.explain(instructions="규칙", input_text="문맥")

    assert responses.calls == 1


def test_quota_error_is_not_retried() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    upstream_response = httpx.Response(429, request=request)

    class QuotaFailureResponses:
        def __init__(self) -> None:
            self.calls = 0

        def create(self, **kwargs):
            del kwargs
            self.calls += 1
            raise openai.RateLimitError(
                "quota unavailable",
                response=upstream_response,
                body={"error": {"code": "insufficient_quota"}},
            )

    responses = QuotaFailureResponses()
    provider = OpenAIProvider(OpenAISettings(api_key="test-key"))
    provider._client = SimpleNamespace(responses=responses)

    with pytest.raises(AIProviderQuotaError):
        provider.explain(instructions="규칙", input_text="문맥")

    assert responses.calls == 1


def test_fallback_log_does_not_include_user_prompt_or_provider_message(
    caplog, monkeypatch, snapshot_path
) -> None:
    sensitive_text = "SECRET_USER_PROMPT_AND_API_KEY"
    client = client_for(
        FailingProvider(AIProviderServerError(sensitive_text)),
        monkeypatch,
        snapshot_path,
    )

    response = client.post("/chat", json={"message": sensitive_text})

    assert response.status_code == 200
    assert sensitive_text not in caplog.text
    assert "reason=SERVER" in caplog.text


def test_llm_context_limits_detailed_candidates_but_response_keeps_contract(
    monkeypatch, snapshot_path
) -> None:
    provider = SuccessfulProvider()
    client = client_for(provider, monkeypatch, snapshot_path)

    response = client.post(
        "/chat",
        json={"message": "창업 지원사업을 알려주세요"},
    )
    payload = response.json()
    context_text = provider.calls[0]["input_text"].split(
        "Structured Context(JSON):\n", maxsplit=1
    )[1]
    context = json.loads(context_text)

    assert len(payload["programs"]) == 5
    assert len(payload["sources"]) == 5
    assert len(payload["actions"]) >= 5
    assert len(context["programs"]) == 3
    assert set(context) == {"user_profile", "programs", "reply_policy"}
    assert set(context["programs"][0]) == {
        "program_id",
        "program_name",
        "provider",
        "eligibility_evidence",
        "deterministic_match",
        "apply_period_text",
        "application_status",
        "application_method_text",
        "source_url",
    }
    assert context["reply_policy"]["detailed_program_limit"] == 3
    assert context["reply_policy"]["visible_token_hard_limit"] == 900
    assert len(context_text) < 4000
    assert "summary_text" not in context_text
    assert "target_text" not in context_text
    assert '"sources"' not in context_text
    assert '"actions"' not in context_text
    assert "최대 3개만 상세 설명" in provider.calls[0]["instructions"]
    assert "준비사항 1순위:" in provider.calls[0]["instructions"]
    assert "준비사항 2순위:" in provider.calls[0]["instructions"]
    assert "준비사항 3순위:" in provider.calls[0]["instructions"]


def test_satisfied_or_path_does_not_require_missing_business_age_in_fallback() -> None:
    context = {
        "programs": [
            {
                "program_id": "PBLN_OR",
                "program_name": "예비창업자 또는 업력 7년 이내 공고",
                "apply_period_text": "2026-09-01 ~ 2026-09-30",
                "application_status": "OPEN",
                "source_url": "https://example.invalid/or",
            }
        ],
        "matches": [
            {
                "program_id": "PBLN_OR",
                "match_status": "NEEDS_REVIEW",
                "reason": "PROGRAM_ELIGIBILITY_NEEDS_REVIEW",
                "condition_results": [
                    {
                        "condition_id": "pre-founder",
                        "condition_type": "pre_founder",
                        "status": "MATCH",
                        "is_exclusion": False,
                        "raw_expected_value": "예비창업자",
                        "reason": "PREDICATE_TRUE",
                    },
                    {
                        "condition_id": "business-age",
                        "condition_type": "business_age",
                        "status": "NEEDS_REVIEW",
                        "is_exclusion": False,
                        "raw_expected_value": "업력 7년 이내",
                        "reason": "REQUIRED_USER_VALUE_MISSING",
                    },
                ],
            }
        ],
        "ignored_or_condition_ids": {"PBLN_OR": ["business-age"]},
    }

    reply = build_template_reply(
        match_status=MatchStatus.NEEDS_REVIEW,
        has_program_context=True,
        has_profile=True,
        structured_context=context,
    )

    assert "추가로 필요한 사용자 정보" not in reply
    assert "부족한 자격조건 정보(업력)" not in reply
    assert "준비사항 1순위:" in reply
    assert "준비사항 2순위:" in reply
    assert "준비사항 3순위:" in reply
