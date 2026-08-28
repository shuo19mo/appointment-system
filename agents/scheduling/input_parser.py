"""DeepSeek structured extraction for multi-turn scheduling requests."""

import json
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, ValidationError

from agents.llm.runtime import LLMRuntime
from agents.scheduling.models import SchedulingRequestData


SHANGHAI = ZoneInfo("Asia/Shanghai")
SCHEDULING_FIELDS = ("student_name", "campus_name", "subject", "grade", "start_at", "duration_minutes", "preferred_teacher_name")


class SchedulingExtraction(BaseModel):
    action: Literal["schedule", "confirm", "cancel"] = "schedule"
    booking_id: int | None = None
    student_name: str | None = None
    campus_name: str | None = None
    subject: str | None = None
    grade: str | None = None
    start_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=360)
    preferred_teacher_name: str | None = None


class LLMSchedulingInputParser:
    def __init__(self, runtime: LLMRuntime, now_provider=None):
        self.runtime = runtime
        self.now_provider = now_provider or (lambda: datetime.now(SHANGHAI))

    def parse(self, text: str, current_state: dict | None = None) -> SchedulingRequestData:
        state = current_state or {}
        safe_state = {key: state.get(key) for key in SCHEDULING_FIELDS if state.get(key) is not None}
        try:
            extracted = self.runtime.structured(
                system=("你是补习机构排课信息提取 Agent。根据当前上海时间解析相对时间。"
                        "只提取用户明确给出或修改的字段；没有提到的字段保持 null。"
                        "确认待选教师用 confirm，取消已有安排用 cancel 并提取 booking_id，其他排课对话用 schedule。"),
                user=(f"当前上海时间：{self.now_provider().astimezone(SHANGHAI).isoformat()}\n"
                      f"已有排课信息：{json.dumps(safe_state, ensure_ascii=False, default=str)}\n"
                      f"用户最新消息：{(text or '').strip()}"),
                schema=SchedulingExtraction,
            )
            provided = {key for key in SCHEDULING_FIELDS if key in extracted.model_fields_set and getattr(extracted, key) is not None}
            merged = dict(safe_state)
            merged.update({key: getattr(extracted, key) for key in provided})
            if merged.get("duration_minutes") is None:
                merged["duration_minutes"] = 90
            return SchedulingRequestData(**merged, action=extracted.action, booking_id=extracted.booking_id, provided_fields=provided)
        except (ValidationError, ValueError, TypeError) as exc:
            raise SchedulingParseError("上课时间或课程时长格式无效") from exc


class SchedulingParseError(ValueError):
    pass
