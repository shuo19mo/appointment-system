"""Deterministic teacher matching and transactional scheduling rules."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from db.models import Teacher
from db.repositories.education_repository import EducationRepository, RepositoryConflict


class ScheduleConflictError(RuntimeError):
    pass


class SchedulingValidationError(ValueError):
    pass


@dataclass(frozen=True)
class TeacherCandidate:
    teacher: Teacher
    score: int
    reasons: tuple[str, ...]
    preferred_teacher_unavailable: bool = False


class SchedulingService:
    def __init__(self, repository: EducationRepository):
        self.repository = repository

    def match_teachers(self, *, student_id: int | None, course_id: int, campus_id: int, start_at: datetime, duration_minutes: int, preferred_teacher_id: int | None = None) -> list[TeacherCandidate]:
        self._validate_time(start_at, duration_minutes)
        end_at = start_at + timedelta(minutes=duration_minutes)
        if student_id is not None and self.repository.has_student_conflict(student_id, start_at, end_at):
            return []

        available = self.repository.eligible_teachers(course_id, campus_id, start_at, end_at)
        available_ids = {teacher.id for teacher in available}
        preferred_unavailable = bool(preferred_teacher_id is not None and preferred_teacher_id not in available_ids)
        course = self.repository.get_course(course_id)
        student = self.repository.get_student(student_id) if student_id is not None else None
        candidates = []
        for teacher in available:
            daily_minutes = self.repository.teacher_daily_minutes(teacher.id, start_at)
            if daily_minutes + duration_minutes > teacher.max_daily_minutes:
                continue
            score = 0
            reasons = ["课程资质、校区和档期均符合"]
            if teacher.id == preferred_teacher_id:
                score += 100
                reasons.append("符合指定教师偏好")
            if student and teacher.id == student.preferred_teacher_id:
                score += 15
                reasons.append("学生历史偏好")
            if course and (course.subject in teacher.specialties or course.grade in teacher.specialties):
                score += 20
                reasons.append("教师专长匹配")
            score += max(0, 10 - daily_minutes // 60)
            reasons.append("当日课时负载较低")
            candidates.append(TeacherCandidate(teacher=teacher, score=score, reasons=tuple(reasons), preferred_teacher_unavailable=preferred_unavailable))
        return sorted(candidates, key=lambda item: (-item.score, item.teacher.name, item.teacher.id))

    def create_booking(self, *, student_id: int, teacher_id: int, course_id: int, campus_id: int, start_at: datetime, duration_minutes: int, notes: str = ""):
        self._validate_time(start_at, duration_minutes)
        if student_id is None:
            raise SchedulingValidationError("创建课程安排必须指定学生")
        end_at = start_at + timedelta(minutes=duration_minutes)
        teacher = self.repository.get_teacher(teacher_id)
        if teacher and self.repository.teacher_daily_minutes(teacher_id, start_at) + duration_minutes > teacher.max_daily_minutes:
            raise SchedulingValidationError("教师当日课时已达到上限")
        eligible_ids = {teacher.id for teacher in self.repository.eligible_teachers(course_id, campus_id, start_at, end_at)}
        if teacher_id not in eligible_ids:
            if self.repository.has_teacher_conflict(teacher_id, start_at, end_at):
                raise ScheduleConflictError("教师在该时段已有课程")
            raise SchedulingValidationError("教师不满足课程、校区或可用时间要求")
        try:
            return self.repository.create_booking_checked(student_id=student_id, teacher_id=teacher_id, course_id=course_id, campus_id=campus_id, start_at=start_at, end_at=end_at, status="confirmed", notes=notes)
        except RepositoryConflict as exc:
            if exc.resource == "teacher":
                raise ScheduleConflictError("教师在该时段已有课程") from exc
            if exc.resource == "student":
                raise ScheduleConflictError("学生在该时段已有课程") from exc
            raise ScheduleConflictError("排课写入繁忙，请稍后重试") from exc

    @staticmethod
    def _validate_time(start_at: datetime, duration_minutes: int) -> None:
        if start_at.tzinfo is None or start_at.utcoffset() is None:
            raise SchedulingValidationError("上课时间必须包含时区")
        if duration_minutes <= 0 or duration_minutes > 360:
            raise SchedulingValidationError("课程时长必须在 1 到 360 分钟之间")
