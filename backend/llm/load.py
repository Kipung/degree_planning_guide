from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from langchain.schema import SystemMessage
from openai import AsyncOpenAI

from utility.backend_log import logger
from .llm_config import SYSTEM_PROMPT


@dataclass(frozen=True)
class LLMConfig:
    model: str
    temperature: float = 0.0
    max_tokens: int | None = None


def _parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return int(value)


@lru_cache(maxsize=1)
def get_llm_config() -> LLMConfig:
    cfg = LLMConfig(
        model=os.environ.get("LLM_MODEL", "mistral"),
        temperature=float(os.environ.get("LLM_TEMPERATURE", "0")),
        max_tokens=_parse_optional_int(os.environ.get("LLM_MAX_TOKENS")),
    )
    logger.debug("Loaded LLM config: %s", cfg)
    return cfg


@lru_cache(maxsize=1)
def get_async_openai_client() -> AsyncOpenAI:
    client = AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", "ollama"),
        base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1"),
    )
    logger.debug("Initialized AsyncOpenAI client with base URL %s", client.base_url)
    return client


def build_system_message() -> SystemMessage:
    return SystemMessage(content=SYSTEM_PROMPT)

