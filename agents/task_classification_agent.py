"""DeepSeek structured-output router for education requests."""

import json
from typing import Literal

from pydantic import BaseModel

from agents.llm.runtime import LLMRuntime


class TaskRoute(BaseModel):
    category: Literal["scheduling", "consultation", "unsupported"]


class TaskClassificationAgent:
    def __init__(self, runtime: LLMRuntime):
        self.runtime = runtime

    def classify(self, text: str, session_state: dict | None = None) -> str:
        state = json.dumps(session_state or {}, ensure_ascii=False, default=str)
        result = self.runtime.structured(
            system=("你是补习机构请求路由 Agent。只按 schema 分类：排课、改期、确认、取消属于 scheduling；"
                    "课程、教师、校区、政策咨询属于 consultation；其他属于 unsupported。不得回答用户问题。"),
            user=f"当前会话状态：{state}\n用户最新消息：{(text or '').strip()}",
            schema=TaskRoute,
        )
        return result.category
