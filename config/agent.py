"""Mandatory DeepSeek Agent configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


class AgentConfigurationError(RuntimeError):
    """Raised when the production Agent runtime is not configured safely."""


@dataclass(frozen=True)
class AgentSettings:
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    timeout_seconds: float = 30.0
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> "AgentSettings":
        mode = os.getenv("AGENT_MODE", "").strip().lower()
        if mode != "llm":
            raise AgentConfigurationError("AGENT_MODE must be llm")
        provider = os.getenv("MODEL_PROVIDER", "").strip().lower()
        if provider != "deepseek":
            raise AgentConfigurationError("MODEL_PROVIDER must be deepseek")
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise AgentConfigurationError("DEEPSEEK_API_KEY is required")
        return cls(
            api_key=api_key,
            base_url=os.getenv("LLM_BASE_URL", "").strip() or "https://api.deepseek.com",
            model=os.getenv("LLM_MODEL", "").strip() or "deepseek-v4-flash",
            timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
            max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
        )
