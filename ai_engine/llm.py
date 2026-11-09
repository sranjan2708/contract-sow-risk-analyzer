"""
LLM abstraction layer.
STUB — owner replaces body, keep signature.
This is the ONLY authorized place in the entire repository to interact with LLMs.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import dotenv
import httpx

# Load .env once at import time so environment variables are available outside FastAPI
dotenv.load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def _get_thinking_config(model: str, thinking_mode: str = "off") -> dict[str, Any] | None:
    """
    Determine the thinking configuration based on model identifier and thinking mode.

    Args:
        model: Target Gemini model identifier.
        thinking_mode: 'off' to reduce/disable thinking, 'default' to omit thinkingConfig.

    Returns:
        dict[str, Any] | None: Thinking configuration dictionary, or None if disabled/omitted.
    """
    if thinking_mode == "default":
        return None

    if "2.5" in model:
        return {"thinkingBudget": 0}

    if model.startswith("gemini-3"):
        return {"thinkingLevel": "low"}

    return None


def _call_gemini(
    prompt: str,
    system: str = "",
    max_tokens: int = 800,
    model: str = "gemini-2.5-flash",
    api_key: str = "",
    timeout_seconds: float = 60.0,
    thinking_mode: str = "off",
) -> str:
    """
    Execute a prompt against the Google Gemini generateContent REST API.

    Args:
        prompt: User input prompt text.
        system: Optional system instruction prompt.
        max_tokens: Maximum tokens to generate.
        model: Target Gemini model identifier.
        api_key: Google Gemini API key.
        timeout_seconds: Request timeout in seconds.
        thinking_mode: Mode controlling thinkingConfig ('off' or 'default').

    Returns:
        str: Generated completion text from candidate parts.

    Raises:
        RuntimeError: On missing API key, network error, HTTP error, or malformed response.
    """
    if not api_key:
        raise RuntimeError("Missing LLM_API_KEY for Gemini provider")

    url = f"{GEMINI_BASE_URL}/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    generation_config: dict[str, Any] = {
        "maxOutputTokens": max_tokens,
    }

    thinking_config = _get_thinking_config(model, thinking_mode)
    if thinking_config is not None:
        generation_config["thinkingConfig"] = thinking_config

    payload: dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": generation_config,
    }

    if system:
        payload["systemInstruction"] = {
            "parts": [{"text": system}],
        }

    timeout_obj = httpx.Timeout(timeout_seconds, connect=10.0)
    max_attempts = 2
    attempt = 0
    call_start = time.perf_counter()

    try:
        while attempt < max_attempts:
            attempt += 1
            try:
                response = httpx.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=timeout_obj,
                )
            except httpx.TimeoutException as exc:
                if attempt < max_attempts:
                    logger.warning(
                        "Gemini API request timed out on attempt %d; retrying once...",
                        attempt,
                    )
                    continue
                raise RuntimeError("Gemini API request timed out after retry") from exc
            except httpx.RequestError as exc:
                raise RuntimeError(
                    f"Gemini API request failed: {type(exc).__name__}"
                ) from exc

            # Retry once without thinkingConfig if HTTP 400 is returned and thinkingConfig was sent
            if response.status_code == 400 and "thinkingConfig" in payload.get("generationConfig", {}):
                logger.warning(
                    "Gemini API returned status 400 with thinkingConfig; retrying once without thinkingConfig..."
                )
                payload["generationConfig"] = {
                    k: v for k, v in payload["generationConfig"].items() if k != "thinkingConfig"
                }
                max_attempts += 1
                continue

            # Retry once on 429 or 5xx
            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt < max_attempts:
                    logger.warning(
                        "Gemini API returned status %d on attempt %d; retrying once...",
                        response.status_code,
                        attempt,
                    )
                    continue
                raise RuntimeError(
                    f"Gemini API returned HTTP status {response.status_code}"
                )

            if response.is_error:
                raise RuntimeError(
                    f"Gemini API returned HTTP status {response.status_code}"
                )

            try:
                data = response.json()
            except Exception as exc:
                raise RuntimeError("Failed to parse Gemini API response as JSON") from exc

            if not isinstance(data, dict):
                raise RuntimeError("Unexpected Gemini response shape: response is not a JSON object")

            candidates = data.get("candidates")
            if not isinstance(candidates, list) or not candidates:
                raise RuntimeError("Gemini returned no text: missing or empty candidates")

            first_candidate = candidates[0]
            if not isinstance(first_candidate, dict):
                raise RuntimeError("Unexpected Gemini response shape: candidate is not a JSON object")

            finish_reason = first_candidate.get("finishReason", "UNKNOWN")

            content = first_candidate.get("content")
            if not isinstance(content, dict):
                raise RuntimeError(f"Gemini returned no text (finishReason={finish_reason})")

            parts = content.get("parts")
            if not isinstance(parts, list) or not parts:
                raise RuntimeError(f"Gemini returned no text (finishReason={finish_reason})")

            text_parts = [
                part["text"]
                for part in parts
                if isinstance(part, dict) and "text" in part and isinstance(part["text"], str)
            ]
            joined_text = "".join(text_parts)
            if not joined_text:
                raise RuntimeError(f"Gemini returned no text (finishReason={finish_reason})")

            return joined_text

        raise RuntimeError("Gemini API request failed")
    finally:
        elapsed = time.perf_counter() - call_start
        logger.info("Gemini API call completed in %.2fs (model=%s)", elapsed, model)


def complete(prompt: str, system: str = "", max_tokens: int = 800) -> str:
    """
    Execute a prompt against the configured LLM provider.

    STUB — owner replaces body, keep signature.

    Args:
        prompt: User input prompt or instruction text.
        system: Optional system prompt setting behavioral constraints.
        max_tokens: Maximum number of tokens to generate.

    Returns:
        str: Model completion response text.

    Raises:
        NotImplementedError: If LLM_PROVIDER is unsupported.
        RuntimeError: If LLM call fails, key is missing, or response is invalid.
    """
    provider = os.getenv("LLM_PROVIDER", "stub").strip().lower()

    if provider == "stub":
        return "[stub LLM response]"

    if provider == "gemini":
        model = os.getenv("LLM_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
        api_key = os.getenv("LLM_API_KEY", "").strip()
        raw_timeout = os.getenv("LLM_TIMEOUT_SECONDS", "60").strip()
        try:
            timeout_seconds = float(raw_timeout)
        except ValueError:
            timeout_seconds = 60.0
        thinking_mode = os.getenv("LLM_THINKING", "off").strip().lower()

        return _call_gemini(
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            model=model,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            thinking_mode=thinking_mode,
        )

    raise NotImplementedError(
        f"LLM provider '{provider}' is not implemented yet. Set LLM_PROVIDER=stub or implement provider in ai_engine/llm.py."
    )
