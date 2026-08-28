from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any


@dataclass
class FakeEmbeddingProvider:
    dimensions: int = 8

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        concepts = (
            (0, ("取消", "退课", "临时有事")),
            (1, ("地址", "校区", "哪里", "张江路")),
            (2, ("教师", "老师", "师资")),
            (3, ("课程", "学科", "数学", "英语")),
        )
        for dimension, terms in concepts:
            if any(term in text for term in terms):
                vector[dimension] += 5.0
        for index, character in enumerate(text):
            vector[index % self.dimensions] += (ord(character) % 17) / 170
        return vector


class FakeLLMRuntime:
    model_name = "fake-deepseek"

    def __init__(
        self,
        *,
        structured: dict[str, list[dict[str, Any]]] | None = None,
        texts: list[str] | None = None,
        tool_results: list[Any] | None = None,
        tool_answer: str = "",
        tool_plan: list[tuple[str, dict[str, Any]]] | None = None,
        error: Exception | None = None,
    ):
        self._structured = defaultdict(deque)
        for schema_name, values in (structured or {}).items():
            self._structured[schema_name].extend(values)
        self._texts = deque(texts or [])
        self._tool_results = deque(tool_results or [])
        self._tool_answer = tool_answer
        self._tool_plan = tool_plan or []
        self._error = error
        self.structured_calls: list[dict[str, Any]] = []
        self.text_calls: list[dict[str, Any]] = []
        self.tool_calls: list[dict[str, Any]] = []

    def structured(self, *, system: str, user: str, schema):
        if self._error:
            raise self._error
        self.structured_calls.append({"system": system, "user": user, "schema": schema.__name__})
        values = self._structured[schema.__name__]
        payload = values.popleft() if values else {}
        return schema.model_validate(payload)

    def text(self, *, system: str, user: str) -> str:
        if self._error:
            raise self._error
        self.text_calls.append({"system": system, "user": user})
        return self._texts.popleft() if self._texts else ""

    def tool_loop(self, *, system: str, user: str, tools: list[Any], max_steps: int = 4):
        if self._error:
            raise self._error
        self.tool_calls.append(
            {"system": system, "user": user, "tools": [tool.name for tool in tools], "max_steps": max_steps}
        )
        if self._tool_results:
            return self._tool_results.popleft()
        from agents.llm.runtime import ToolLoopResult

        trace = []
        registry = {tool.name: tool for tool in tools}
        for name, args in self._tool_plan:
            tool = registry[name]
            tool.handler(tool.args_schema.model_validate(args))
            trace.append(f"{name}: success")

        return ToolLoopResult(answer=self._tool_answer, trace=tuple(trace))
