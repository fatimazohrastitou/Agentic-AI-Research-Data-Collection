"""Optional LLM configuration for Part 2.

Part 1 never requires an API key. Part 2 uses a LLM when OPENAI_API_KEY
(or ANTHROPIC_API_KEY) is present; otherwise agents fall back to transparent
heuristic / template logic so the pipeline remains runnable offline.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def llm_mode() -> str:
    """Return 'openai', 'anthropic', or 'heuristic'."""
    if os.getenv("OPENAI_API_KEY", "").strip():
        return "openai"
    if os.getenv("ANTHROPIC_API_KEY", "").strip():
        return "anthropic"
    return "heuristic"


@lru_cache(maxsize=1)
def get_chat_model(temperature: float = 0.1) -> Any | None:
    """Return a LangChain chat model, or None in heuristic mode."""
    mode = llm_mode()
    if mode == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise ImportError(
                "langchain-openai is required when OPENAI_API_KEY is set. "
                "Install with: pip install langchain-openai"
            ) from exc
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return ChatOpenAI(model=model, temperature=temperature)
    if mode == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise ImportError(
                "langchain-anthropic is required when ANTHROPIC_API_KEY is set. "
                "Install with: pip install langchain-anthropic"
            ) from exc
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
        return ChatAnthropic(model=model, temperature=temperature)
    return None


def invoke_llm(system: str, user: str, temperature: float = 0.1) -> str | None:
    """Invoke the configured LLM and return plain text, or None if unavailable."""
    model = get_chat_model(temperature=temperature)
    if model is None:
        return None
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        response = model.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        content = getattr(response, "content", response)
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    parts.append(str(block["text"]))
                else:
                    parts.append(str(block))
            return "\n".join(parts).strip()
        return str(content).strip()
    except Exception as exc:  # Keep pipeline resilient; callers use heuristics.
        return f"[llm_error] {type(exc).__name__}: {exc}"
