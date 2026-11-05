"""
LLM abstraction layer.
STUB — owner replaces body, keep signature.
This is the ONLY authorized place in the entire repository to interact with LLMs.
"""
from __future__ import annotations

import os


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
        NotImplementedError: If LLM_PROVIDER is not 'stub'.
    """
    provider = os.getenv("LLM_PROVIDER", "stub").strip().lower()

    if provider == "stub":
        return "[stub LLM response]"

    raise NotImplementedError(
        f"LLM provider '{provider}' is not implemented yet. Set LLM_PROVIDER=stub or implement provider in ai_engine/llm.py."
    )
