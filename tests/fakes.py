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
        for index, character in enumerate(text):
            vector[index % self.dimensions] += (ord(character) % 97) / 97
        return vector


class FakeLLMRuntime:
    model_name = "fake-deepseek"

    def __init__(
        self,
        *,
        structured: dict[str, list[dict[str, Any]]] | None = None,
        texts: list[str] | None = None,
        tool_results: list[Any] | None = None,
    ):
        self._structured = defaultdict(deque)
        for schema_name, values in (structured or {}).items():
            self._structured[schema_name].extend(values)
        self._texts = deque(texts or [])
        self._tool_results = deque(tool_results or [])
        self.structured_calls: list[dict[str, Any]] = []
        self.text_calls: list[dict[str, Any]] = []
        self.tool_calls: list[dict[str, Any]] = []

    def structured(self, *, system: str, user: str, schema):
        self.structured_calls.append({"system": system, "user": user, "schema": schema.__name__})
        values = self._structured[schema.__name__]
        payload = values.popleft() if values else {}
        return schema.model_validate(payload)

    def text(self, *, system: str, user: str) -> str:
        self.text_calls.append({"system": system, "user": user})
        return self._texts.popleft() if self._texts else ""

    def tool_loop(self, *, system: str, user: str, tools: list[Any], max_steps: int = 4):
        self.tool_calls.append(
            {"system": system, "user": user, "tools": [tool.name for tool in tools], "max_steps": max_steps}
        )
        if self._tool_results:
            return self._tool_results.popleft()
        from agents.llm.runtime import ToolLoopResult

        return ToolLoopResult(answer="", trace=[])
