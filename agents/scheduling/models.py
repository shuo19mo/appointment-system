from datetime import datetime

from pydantic import BaseModel, Field


FIELD_LABELS = {"student": "学生姓名", "campus": "校区", "subject": "学科", "grade": "年级", "start_at": "上课时间"}


class SchedulingRequestData(BaseModel):
    student_name: str | None = None
    campus_name: str | None = None
    subject: str | None = None
    grade: str | None = None
    start_at: datetime | None = None
    duration_minutes: int = Field(default=90, ge=1, le=360)
    preferred_teacher_name: str | None = None
    provided_fields: set[str] = Field(default_factory=set, exclude=True)

    def missing_fields(self) -> list[str]:
        fields = []
        if not self.student_name:
            fields.append("student")
        if not self.campus_name:
            fields.append("campus")
        if not self.subject:
            fields.append("subject")
        if not self.grade:
            fields.append("grade")
        if not self.start_at:
            fields.append("start_at")
        return fields

    def follow_up_question(self) -> str:
        missing = self.missing_fields()
        if not missing:
            return "信息已完整，可以查询教师档期。"
        return f"还需要补充：{'、'.join(FIELD_LABELS[item] for item in missing)}。"
