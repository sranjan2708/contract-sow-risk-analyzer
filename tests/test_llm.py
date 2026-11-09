"""
Tests for LLM abstraction layer (ai_engine/llm.py).
Ensures stub works, gemini calls REST API with proper auth, headers,
thinkingConfig handling, timeout configuration, retries, and finishReason checks.
"""
from __future__ import annotations

import copy
from typing import Any
import httpx
import pytest

from ai_engine.llm import complete


@pytest.fixture(autouse=True)
def clean_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate tests from any developer local .env values."""
    monkeypatch.delenv("LLM_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("LLM_THINKING", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "stub")


def test_stub_returns_stub_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify stub provider returns '[stub LLM response]' exactly."""
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    response = complete("Analyze this clause", system="Be concise")
    assert response == "[stub LLM response]"


def test_gemini_success_with_monkeypatched_httpx(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify Gemini provider posts to correct URL without key in URL,
    sends key in x-goog-api-key header, sends correct payload,
    and returns joined candidate parts.
    """
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("LLM_API_KEY", "super-secret-gemini-key")

    captured_requests: list[dict[str, Any]] = []

    def mock_post(url: str, **kwargs: Any) -> httpx.Response:
        captured_requests.append({"url": url, **copy.deepcopy(kwargs)})
        return httpx.Response(
            status_code=200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "Risk analysis: "},
                                {"text": "High exposure detected."},
                            ],
                            "role": "model",
                        },
                        "finishReason": "STOP",
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx, "post", mock_post)

    result = complete(
        prompt="Review clause 4.2",
        system="You are a legal risk analyst.",
        max_tokens=600,
    )

    assert result == "Risk analysis: High exposure detected."
    assert len(captured_requests) == 1

    req = captured_requests[0]
    # Assert URL does NOT have the secret key
    assert "super-secret-gemini-key" not in req["url"]
    assert req["url"] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

    # Assert header has the key
    assert req["headers"]["x-goog-api-key"] == "super-secret-gemini-key"

    # Assert payload structure (2.5 model has thinkingBudget: 0 by default)
    payload = req["json"]
    assert payload["contents"] == [{"role": "user", "parts": [{"text": "Review clause 4.2"}]}]
    assert payload["systemInstruction"] == {"parts": [{"text": "You are a legal risk analyst."}]}
    assert payload["generationConfig"]["maxOutputTokens"] == 600
    assert payload["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}

    # Assert default timeout is 60s with 10s connect
    timeout = req["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.read == 60.0
    assert timeout.connect == 10.0


def test_gemini_thinking_config_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify:
    - 2.5 model sends thinkingBudget: 0
    - gemini-3 model sends thinkingLevel: 'low'
    - LLM_THINKING=default sends no thinkingConfig
    """
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_API_KEY", "super-secret-gemini-key")

    captured_configs: list[dict[str, Any]] = []

    def mock_post(url: str, **kwargs: Any) -> httpx.Response:
        captured_configs.append(copy.deepcopy(kwargs["json"]["generationConfig"]))
        return httpx.Response(
            status_code=200,
            json={"candidates": [{"content": {"parts": [{"text": "OK"}]}}]},
        )

    monkeypatch.setattr(httpx, "post", mock_post)

    # 1. 2.5 model with default thinking (off)
    monkeypatch.setenv("LLM_MODEL", "gemini-2.5-flash")
    monkeypatch.delenv("LLM_THINKING", raising=False)
    complete("Test 2.5")
    assert captured_configs[-1]["thinkingConfig"] == {"thinkingBudget": 0}

    # 2. gemini-3 model with default thinking (off)
    monkeypatch.setenv("LLM_MODEL", "gemini-3-flash")
    complete("Test 3.x")
    assert captured_configs[-1]["thinkingConfig"] == {"thinkingLevel": "low"}

    # 3. LLM_THINKING=default sends no thinkingConfig
    monkeypatch.setenv("LLM_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("LLM_THINKING", "default")
    complete("Test default")
    assert "thinkingConfig" not in captured_configs[-1]

    # 4. Other models (e.g. gemini-1.5) send no thinkingConfig
    monkeypatch.setenv("LLM_MODEL", "gemini-1.5-pro")
    monkeypatch.setenv("LLM_THINKING", "off")
    complete("Test 1.5")
    assert "thinkingConfig" not in captured_configs[-1]


def test_custom_timeout_passed_to_httpx(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify custom LLM_TIMEOUT_SECONDS is configured on httpx.Timeout."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_API_KEY", "super-secret-gemini-key")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "45")

    captured_timeouts: list[Any] = []

    def mock_post(url: str, **kwargs: Any) -> httpx.Response:
        captured_timeouts.append(kwargs["timeout"])
        return httpx.Response(
            status_code=200,
            json={"candidates": [{"content": {"parts": [{"text": "OK"}]}}]},
        )

    monkeypatch.setattr(httpx, "post", mock_post)

    complete("Test timeout")
    assert len(captured_timeouts) == 1
    timeout = captured_timeouts[0]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.read == 45.0
    assert timeout.connect == 10.0


def test_400_with_thinking_config_retries_without_and_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify HTTP 400 when thinkingConfig was sent retries once without thinkingConfig and succeeds."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("LLM_API_KEY", "super-secret-gemini-key")
    monkeypatch.setenv("LLM_THINKING", "off")

    calls: list[dict[str, Any]] = []

    def mock_post(url: str, **kwargs: Any) -> httpx.Response:
        calls.append(copy.deepcopy(kwargs["json"]))
        if len(calls) == 1:
            return httpx.Response(status_code=400, text="Bad Request: thinkingConfig not supported")
        return httpx.Response(
            status_code=200,
            json={"candidates": [{"content": {"parts": [{"text": "OK without thinking"}]}}]},
        )

    monkeypatch.setattr(httpx, "post", mock_post)

    result = complete("Say OK")
    assert result == "OK without thinking"
    assert len(calls) == 2
    # First attempt had thinkingConfig
    assert "thinkingConfig" in calls[0]["generationConfig"]
    # Second attempt had thinkingConfig removed
    assert "thinkingConfig" not in calls[1]["generationConfig"]


def test_empty_candidates_or_parts_raises_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verify empty candidates, empty parts, or finishReason with no text
    raises RuntimeError with finishReason in the message.
    """
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_API_KEY", "super-secret-gemini-key")

    # 1. Missing / empty candidates
    monkeypatch.setattr(
        httpx, "post", lambda url, **kwargs: httpx.Response(status_code=200, json={"candidates": []})
    )
    with pytest.raises(RuntimeError) as exc1:
        complete("Test prompt")
    assert "candidates" in str(exc1.value)

    # 2. Empty parts with finishReason MAX_TOKENS
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kwargs: httpx.Response(
            status_code=200,
            json={
                "candidates": [
                    {
                        "finishReason": "MAX_TOKENS",
                        "content": {"parts": []},
                    }
                ]
            },
        ),
    )
    with pytest.raises(RuntimeError) as exc2:
        complete("Test prompt")
    assert "finishReason=MAX_TOKENS" in str(exc2.value)

    # 3. Missing content with finishReason SAFETY
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kwargs: httpx.Response(
            status_code=200,
            json={
                "candidates": [
                    {
                        "finishReason": "SAFETY",
                    }
                ]
            },
        ),
    )
    with pytest.raises(RuntimeError) as exc3:
        complete("Test prompt")
    assert "finishReason=SAFETY" in str(exc3.value)

    # 4. Empty text inside parts
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kwargs: httpx.Response(
            status_code=200,
            json={
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {"parts": [{"text": ""}]},
                    }
                ]
            },
        ),
    )
    with pytest.raises(RuntimeError) as exc4:
        complete("Test prompt")
    assert "finishReason=STOP" in str(exc4.value)


def test_gemini_omits_system_instruction_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify systemInstruction is omitted when system is empty."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_API_KEY", "super-secret-gemini-key")

    captured_requests: list[dict[str, Any]] = []

    def mock_post(url: str, **kwargs: Any) -> httpx.Response:
        captured_requests.append({"url": url, **copy.deepcopy(kwargs)})
        return httpx.Response(
            status_code=200,
            json={"candidates": [{"content": {"parts": [{"text": "Hello"}]}}]},
        )

    monkeypatch.setattr(httpx, "post", mock_post)

    result = complete("Say hello", system="")
    assert result == "Hello"
    assert "systemInstruction" not in captured_requests[0]["json"]


def test_gemini_500_twice_raises_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify 500 error triggers a retry and then raises RuntimeError with no key exposed."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_API_KEY", "super-secret-gemini-key")

    call_count = 0

    def mock_post(url: str, **kwargs: Any) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(status_code=500, text="Internal Server Error")

    monkeypatch.setattr(httpx, "post", mock_post)

    with pytest.raises(RuntimeError) as exc_info:
        complete("Test prompt")

    assert call_count == 2
    assert "super-secret-gemini-key" not in str(exc_info.value)
    assert "500" in str(exc_info.value)


def test_gemini_500_retry_once_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify 500 error on first attempt retries and succeeds if second attempt returns 200."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_API_KEY", "super-secret-gemini-key")

    attempts = 0

    def mock_post(url: str, **kwargs: Any) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(status_code=500, text="Transient Error")
        return httpx.Response(
            status_code=200,
            json={"candidates": [{"content": {"parts": [{"text": "Success after retry"}]}}]},
        )

    monkeypatch.setattr(httpx, "post", mock_post)

    result = complete("Test prompt")
    assert attempts == 2
    assert result == "Success after retry"


def test_gemini_429_retry_once_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify 429 rate limit triggers a retry and succeeds."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_API_KEY", "super-secret-gemini-key")

    attempts = 0

    def mock_post(url: str, **kwargs: Any) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(status_code=429, text="Rate limit exceeded")
        return httpx.Response(
            status_code=200,
            json={"candidates": [{"content": {"parts": [{"text": "Recovered from 429"}]}}]},
        )

    monkeypatch.setattr(httpx, "post", mock_post)

    result = complete("Test prompt")
    assert attempts == 2
    assert result == "Recovered from 429"


def test_gemini_timeout_twice_raises_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify timeout on both attempts raises RuntimeError without exposing key."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_API_KEY", "super-secret-gemini-key")

    call_count = 0

    def mock_post(url: str, **kwargs: Any) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        raise httpx.ReadTimeout("Timed out waiting for response")

    monkeypatch.setattr(httpx, "post", mock_post)

    with pytest.raises(RuntimeError) as exc_info:
        complete("Test prompt")

    assert call_count == 2
    assert "super-secret-gemini-key" not in str(exc_info.value)
    assert "timed out" in str(exc_info.value).lower()


def test_gemini_missing_api_key_raises_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify missing or empty LLM_API_KEY raises RuntimeError."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        complete("Test prompt")

    assert "LLM_API_KEY" in str(exc_info.value)

    monkeypatch.setenv("LLM_API_KEY", "   ")
    with pytest.raises(RuntimeError) as exc_info2:
        complete("Test prompt")

    assert "LLM_API_KEY" in str(exc_info2.value)


def test_unknown_provider_raises_not_implemented_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify unsupported provider string raises NotImplementedError."""
    monkeypatch.setenv("LLM_PROVIDER", "unsupported_provider")

    with pytest.raises(NotImplementedError) as exc_info:
        complete("Test prompt")

    assert "unsupported_provider" in str(exc_info.value)
