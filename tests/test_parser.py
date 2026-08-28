from datetime import datetime
from zoneinfo import ZoneInfo

from agents.scheduling.input_parser import SchedulingInputParser


def test_parser_extracts_education_scheduling_fields():
    parser = SchedulingInputParser()

    result = parser.parse(
        "给小明在浦东校区约初二数学，2026-09-05 14:00，90分钟，最好王老师"
    )

    assert result.student_name == "小明"
    assert result.campus_name == "浦东校区"
    assert result.subject == "数学"
    assert result.grade == "初二"
    assert result.start_at == datetime(2026, 9, 5, 14, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    assert result.duration_minutes == 90
    assert result.preferred_teacher_name == "王老师"


def test_parser_returns_targeted_question_for_missing_fields():
    parser = SchedulingInputParser()
    result = parser.parse("想约数学课")

    assert set(result.missing_fields()) == {"student", "campus", "grade", "start_at"}
    question = result.follow_up_question()
    assert "学生" in question
    assert "校区" in question
    assert "年级" in question
    assert "上课时间" in question


def test_parser_understands_common_relative_chinese_time():
    parser = SchedulingInputParser(
        now_provider=lambda: datetime(2026, 8, 28, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    )

    tomorrow = parser.parse("给小明在浦东校区约初二数学，明天下午2点")
    saturday = parser.parse("给小明在浦东校区约初二数学，本周六下午3点")

    assert tomorrow.start_at == datetime(2026, 8, 29, 14, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    assert saturday.start_at == datetime(2026, 8, 29, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai"))


def test_parser_accepts_standard_iso_time_with_offset():
    parser = SchedulingInputParser()

    result = parser.parse(
        "给小明在浦东校区约初二数学，2026-09-05T14:00:00+08:00，60分钟"
    )

    assert result.start_at == datetime.fromisoformat("2026-09-05T14:00:00+08:00")
    assert result.duration_minutes == 60
