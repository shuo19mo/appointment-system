"""DeepSeek-backed runtime with safe, testable interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel

from config.agent import AgentSettings


class LLMUnavailableError(RuntimeError):
    """Raised when DeepSeek cannot complete an Agent request."""


@dataclass(frozen=True)
class ToolLoopResult:
    answer: str
    trace: list[dict[str, Any]] = field(default_factory=list)


class LLMRuntime(Protocol):
    model_name: str

    def structured(self, *, system: str, user: str, schema: type[BaseModel]) -> BaseModel: ...
    def text(self, *, system: str, user: str) -> str: ...
    def tool_loop(self, *, system: str, user: str, tools: list[Any], max_steps: int = 4) -> ToolLoopResult: ...


class DeepSeekLLMRuntime:
    def __init__(self, settings: AgentSettings, *, chat_model=None):
        if chat_model is None:
            from config.model_provider import create_deepseek_chat_model

            chat_model = create_deepseek_chat_model(settings)
        self._chat_model = chat_model
        self.model_name = settings.model

    @staticmethod
    def _messages(system: str, user: str) -> list[tuple[str, str]]:
        return [("system", system), ("human", user)]

    def structured(self, *, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        try:
            model = self._chat_model.with_structured_output(schema)
            result = model.invoke(self._messages(system, user))
            return result if isinstance(result, schema) else schema.model_validate(result)
        except Exception as exc:
            raise LLMUnavailableError("DeepSeek 服务暂时不可用") from exc

    def text(self, *, system: str, user: str) -> str:
        try:
            result = self._chat_model.invoke(self._messages(system, user))
            content = getattr(result, "content", result)
            return str(content)
        except Exception as exc:
            raise LLMUnavailableError("DeepSeek 服务暂时不可用") from exc

    def tool_loop(self, *, system: str, user: str, tools: list[Any], max_steps: int = 4) -> ToolLoopResult:
        raise NotImplementedError("Tool loop is implemented with the bounded Agent tools")


def create_deepseek_runtime(settings: AgentSettings) -> DeepSeekLLMRuntime:
    return DeepSeekLLMRuntime(settings)
