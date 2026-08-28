from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from agents.scheduling.input_parser import LLMSchedulingInputParser
from tests.fakes import FakeLLMRuntime


def test_parser_extracts_structured_education_fields_with_llm():
    runtime = FakeLLMRuntime(
        structured={
            "SchedulingExtraction": [
                {
                    "action": "schedule",
                    "student_name": "小明",
                    "campus_name": "浦东校区",
                    "subject": "数学",
                    "grade": "初二",
                    "start_at": "2026-09-05T14:00:00+08:00",
                    "duration_minutes": 90,
                    "preferred_teacher_name": "王老师",
                }
            ]
        }
    )
    parser = LLMSchedulingInputParser(runtime)

    result = parser.parse("随便一段不含可供规则识别的文本", {})

    assert result.student_name == "小明"
    assert result.start_at == datetime(2026, 9, 5, 14, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    assert result.preferred_teacher_name == "王老师"
    assert "student_name" in result.provided_fields
    assert runtime.structured_calls[0]["schema"] == "SchedulingExtraction"


def test_parser_merges_only_fields_provided_by_llm():
    runtime = FakeLLMRuntime(
        structured={"SchedulingExtraction": [{"action": "schedule", "duration_minutes": 90}]}
    )
    parser = LLMSchedulingInputParser(runtime)

    result = parser.parse(
        "改一下",
        {"student_name": "小明", "campus_name": "浦东校区", "duration_minutes": 60},
    )

    assert result.student_name == "小明"
    assert result.duration_minutes == 90
    assert result.provided_fields == {"duration_minutes"}


def test_parser_uses_llm_for_relative_chinese_time():
    runtime = FakeLLMRuntime(
        structured={
            "SchedulingExtraction": [
                {"action": "schedule", "start_at": "2026-08-29T14:00:00+08:00"}
            ]
        }
    )
    parser = LLMSchedulingInputParser(
        runtime,
        now_provider=lambda: datetime(2026, 8, 28, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    result = parser.parse("明天下午2点", {})

    assert result.start_at == datetime(2026, 8, 29, 14, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    assert "2026-08-28" in runtime.structured_calls[0]["user"]


def test_production_chat_path_has_no_rule_fallback():
    forbidden = ("SCHEDULING_TERMS", "CONSULTATION_TERMS", "_parse_relative_time")
    paths = [Path("agents/task_classification_agent.py"), Path("agents/scheduling/input_parser.py")]
    source = "\n".join(path.read_text() for path in paths)

    assert not any(term in source for term in forbidden)
