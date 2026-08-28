"""DeepSeek-backed runtime with safe, testable interfaces."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Protocol

from pydantic import BaseModel

from config.agent import AgentSettings


class LLMUnavailableError(RuntimeError):
    """Raised when DeepSeek cannot complete an Agent request."""


@dataclass(frozen=True)
class ToolLoopResult:
    answer: str
    trace: tuple[str, ...] = ()


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
            model = self._chat_model.with_structured_output(schema, method="function_calling")
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
        if not 1 <= max_steps <= 4:
            raise ValueError("max_steps must be between 1 and 4")
        try:
            from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
            from langchain_core.tools import StructuredTool

            tool_map = {tool.name: tool for tool in tools}
            structured_tools = []
            for tool in tools:
                def invoke_tool(_tool=tool, **kwargs):
                    return _tool.handler(_tool.args_schema.model_validate(kwargs))

                structured_tools.append(
                    StructuredTool.from_function(
                        func=invoke_tool,
                        name=tool.name,
                        description=tool.description,
                        args_schema=tool.args_schema,
                    )
                )
            model = self._chat_model.bind_tools(structured_tools)
            messages = [SystemMessage(content=system), HumanMessage(content=user)]
            trace: list[str] = []
            for _ in range(max_steps):
                response = model.invoke(messages)
                messages.append(response)
                calls = getattr(response, "tool_calls", None) or []
                if not calls:
                    return ToolLoopResult(answer=str(getattr(response, "content", "")), trace=tuple(trace))
                for call in calls:
                    name = call.get("name", "unknown")
                    tool = tool_map.get(name)
                    try:
                        if tool is None:
                            raise ValueError("unknown tool")
                        result = tool.handler(tool.args_schema.model_validate(call.get("args", {})))
                        count = len(result.get("candidates", [])) if isinstance(result, dict) and "candidates" in result else None
                        status = f"{count} candidates" if count is not None else "success"
                        content = json.dumps(result, ensure_ascii=False, default=str)
                    except Exception:
                        status = "error"
                        content = json.dumps({"error": "工具执行失败"}, ensure_ascii=False)
                    trace.append(f"{name}: {status}")
                    messages.append(ToolMessage(content=content, tool_call_id=call.get("id", name)))
            return ToolLoopResult(answer="已完成资料查询，请缩小问题范围后重试。", trace=tuple(trace))
        except LLMUnavailableError:
            raise
        except Exception as exc:
            raise LLMUnavailableError("DeepSeek 服务暂时不可用") from exc


def create_deepseek_runtime(settings: AgentSettings) -> DeepSeekLLMRuntime:
    return DeepSeekLLMRuntime(settings)
