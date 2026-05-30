"""LLM factory — decouples the pipeline graph from any specific SDK."""

import json
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

LLMCallable = Callable[[str, str], Awaitable[str]]
LLMFactory = Callable[[str], LLMCallable]


def make_anthropic_llm(api_key: str | None = None) -> LLMFactory:
    """Return an LLMFactory backed by the Anthropic Messages API."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=api_key, timeout=120.0)

    def make_llm(model: str) -> LLMCallable:
        async def call(system: str, user: str) -> str:
            logger.debug("LLM call model=%s system_chars=%d", model, len(system))
            message = await client.messages.create(
                model=model,
                max_tokens=4_096,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return message.content[0].text

        return call

    return make_llm


def make_stub_llm(
    responses: dict[str, str] | None = None,
    default: str | None = None,
) -> LLMFactory:
    """Testing factory returning canned responses keyed on system-prompt substrings."""
    _fallback = default or json.dumps({
        "key_points": ["Stub response."],
        "recommendation": "hold",
        "confidence": 0.5,
    })

    def make_llm(model: str) -> LLMCallable:
        async def call(system: str, user: str) -> str:
            if responses:
                s = system.lower()
                for key, reply in responses.items():
                    if key.lower() in s:
                        return reply
            return _fallback

        return call

    return make_llm
