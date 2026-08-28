"""Offline-first parser for common Chinese scheduling requests."""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from agents.scheduling.models import SchedulingRequestData


SHANGHAI = ZoneInfo("Asia/Shanghai")
SUBJECTS = ("数学", "英语", "语文", "物理", "化学", "生物", "历史", "地理", "政治")
GRADES = ("一年级", "二年级", "三年级", "四年级", "五年级", "六年级", "初一", "初二", "初三", "高一", "高二", "高三")


class SchedulingInputParser:
    def __init__(self, now_provider=None):
        self.now_provider = now_provider or (lambda: datetime.now(SHANGHAI))

    def parse(self, text: str) -> SchedulingRequestData:
        text = (text or "").strip()
        subject = next((item for item in SUBJECTS if item in text), None)
        grade = next((item for item in GRADES if item in text), None)
        student_match = re.search(r"(?:给|学生[:：]?)([\u4e00-\u9fa5A-Za-z·]{2,12}?)(?:在|约|上)", text)
        campus_match = re.search(r"(?:在|到)([\u4e00-\u9fa5A-Za-z0-9·]{1,12}校区)", text)
        if campus_match is None:
            campus_match = re.search(r"([\u4e00-\u9fa5A-Za-z0-9·]{1,12}校区)", text)
        teacher_match = re.search(r"(?:最好|指定|想找|由)([\u4e00-\u9fa5A-Za-z·]{1,8}老师)", text)
        if teacher_match is None:
            teacher_match = re.search(r"([\u4e00-\u9fa5A-Za-z·]{1,8}老师)", text)
        duration_match = re.search(r"(\d{1,3})\s*分钟", text)
        iso_match = re.search(r"20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})", text)
        local_match = re.search(r"(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})(?:日)?\s+(\d{1,2})[:：](\d{2})", text)
        try:
            if iso_match:
                start_at = datetime.fromisoformat(iso_match.group(0).replace("Z", "+00:00"))
            elif local_match:
                start_at = datetime(*(int(value) for value in local_match.groups()), tzinfo=SHANGHAI)
            else:
                start_at = self._parse_relative_time(text)
            provided_fields = {"duration_minutes"} if duration_match else set()
            return SchedulingRequestData(
                student_name=student_match.group(1) if student_match else None,
                campus_name=campus_match.group(1) if campus_match else None,
                subject=subject,
                grade=grade,
                start_at=start_at,
                duration_minutes=int(duration_match.group(1)) if duration_match else 90,
                preferred_teacher_name=teacher_match.group(1) if teacher_match else None,
                provided_fields=provided_fields,
            )
        except (ValueError, OverflowError) as exc:
            raise SchedulingParseError("上课时间或课程时长格式无效") from exc

    def _parse_relative_time(self, text: str) -> datetime | None:
        now = self.now_provider().astimezone(SHANGHAI)
        tomorrow = re.search(r"明天(上午|中午|下午|晚上)?\s*(\d{1,2})点(半|\d{1,2}分)?", text)
        if tomorrow:
            hour, minute = self._clock_parts(tomorrow.group(1), tomorrow.group(2), tomorrow.group(3))
            return (now + timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)

        weekday = re.search(r"(本周|下周)?周([一二三四五六日天])(上午|中午|下午|晚上)?\s*(\d{1,2})点(半|\d{1,2}分)?", text)
        if weekday:
            target = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}[weekday.group(2)]
            days = (target - now.weekday()) % 7
            if weekday.group(1) == "下周":
                days += 7 if days else 7
            hour, minute = self._clock_parts(weekday.group(3), weekday.group(4), weekday.group(5))
            return (now + timedelta(days=days)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        return None

    @staticmethod
    def _clock_parts(period: str | None, hour_text: str, minute_text: str | None) -> tuple[int, int]:
        hour = int(hour_text)
        if period in ("下午", "晚上") and hour < 12:
            hour += 12
        elif period == "中午" and hour < 11:
            hour += 12
        minute = 30 if minute_text == "半" else int(minute_text[:-1]) if minute_text else 0
        return hour, minute


class SchedulingParseError(ValueError):
    pass
