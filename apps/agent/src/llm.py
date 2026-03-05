from __future__ import annotations

import httpx
from livekit.plugins import openai
from settings import AgentSettings


def build_llm(settings: AgentSettings) -> openai.LLM:
    base_url = settings.LITELLM_URL.rstrip("/") + "/v1"

    return openai.LLM(
        base_url=base_url,
        api_key=settings.LITELLM_MASTER_KEY,
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_completion_tokens=settings.LLM_MAX_TOKENS,
        timeout=httpx.Timeout(15.0),
    )
