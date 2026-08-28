"""LLM-directed, server-guarded scheduling orchestration."""

from datetime import datetime
from zoneinfo import ZoneInfo

from agents.llm.runtime import LLMRuntime
from agents.scheduling.input_parser import LLMSchedulingInputParser
from agents.scheduling.models import SchedulingRequestData
from agents.session_store import SessionStore
from db.repositories.education_repository import EducationRepository
from services.scheduling_service import ScheduleConflictError, SchedulingService


class SchedulingAgent:
    def __init__(self, repository: EducationRepository, session_store: SessionStore, runtime: LLMRuntime):
        self.repository = repository
        self.session_store = session_store
        self.parser = LLMSchedulingInputParser(runtime)
        self.service = SchedulingService(repository)

    def process(self, session_id: str, message: str) -> dict:
        previous_state = self.session_store.get(session_id)
        parsed = self.parser.parse((message or "").strip(), previous_state)
        if parsed.action == "cancel":
            return self._cancel_booking(parsed.booking_id)
        if parsed.action == "confirm":
            return self._confirm_pending_booking(session_id, parsed.preferred_teacher_name)

        updates = {key: value for key, value in parsed.model_dump().items() if value is not None}
        state = self.session_store.update(session_id, updates)
        request = SchedulingRequestData.model_validate(state)
        if request.missing_fields():
            return {"category": "scheduling", "status": "collecting", "answer": request.follow_up_question(), "data": request.model_dump(mode="json")}

        student = self.repository.find_student(request.student_name)
        campus = self.repository.find_campus(request.campus_name)
        course = self.repository.find_course(request.subject, request.grade)
        teacher = self.repository.find_teacher(request.preferred_teacher_name) if request.preferred_teacher_name else None
        missing_records = []
        if student is None:
            missing_records.append("学生")
        if campus is None:
            missing_records.append("校区")
        if course is None:
            missing_records.append("课程")
        if request.preferred_teacher_name and teacher is None:
            missing_records.append("教师")
        if missing_records:
            return {"category": "scheduling", "status": "not_found", "answer": f"未找到匹配的{'、'.join(missing_records)}记录，请先由教务维护基础资料。"}

        candidates = self.service.match_teachers(
            student_id=student.id, course_id=course.id, campus_id=campus.id,
            start_at=request.start_at, duration_minutes=request.duration_minutes,
            preferred_teacher_id=teacher.id if teacher else None,
        )
        if not candidates:
            return {"category": "scheduling", "status": "no_availability", "answer": "该时间没有满足条件的教师，建议调整上课时间。", "candidates": []}
        payload = {
            "student_id": student.id, "course_id": course.id, "campus_id": campus.id,
            "start_at": request.start_at.isoformat(), "duration_minutes": request.duration_minutes,
            "candidate_teacher_ids": [item.teacher.id for item in candidates],
        }
        self.session_store.update(session_id, {"pending_booking": payload})
        names = "、".join(item.teacher.name for item in candidates)
        return {
            "category": "scheduling", "status": "matched",
            "answer": f"已查询教师档期，可选教师：{names}。请回复“确认 + 教师姓名”完成排课。",
            "candidates": [{"teacher_id": item.teacher.id, "teacher_name": item.teacher.name, "score": item.score, "reasons": list(item.reasons)} for item in candidates],
        }

    def _cancel_booking(self, booking_id: int | None) -> dict:
        if booking_id is None:
            return {"category": "scheduling", "status": "missing_booking_id", "answer": "请提供要取消的课程安排编号。"}
        booking = self.repository.cancel_booking(booking_id)
        if booking is None:
            return {"category": "scheduling", "status": "not_found", "answer": "未找到该课程安排。"}
        return {"category": "scheduling", "status": "cancelled", "answer": f"课程安排 #{booking.id} 已取消。", "booking_id": booking.id}

    def _confirm_pending_booking(self, session_id: str, preferred_teacher_name: str | None) -> dict:
        pending = self.session_store.get(session_id).get("pending_booking")
        if not pending:
            return {"category": "scheduling", "status": "missing_context", "answer": "当前没有待确认的排课，请先提供学生、课程、校区和时间。"}
        teacher_id = None
        teacher_name = None
        for candidate_id in pending["candidate_teacher_ids"]:
            teacher = self.repository.get_teacher(candidate_id)
            if teacher and (preferred_teacher_name is None or teacher.name == preferred_teacher_name):
                teacher_id, teacher_name = teacher.id, teacher.name
                break
        if teacher_id is None:
            return {"category": "scheduling", "status": "invalid_confirmation", "answer": "请确认候选列表中的教师姓名。"}
        try:
            booking = self.service.create_booking(
                student_id=pending["student_id"], teacher_id=teacher_id,
                course_id=pending["course_id"], campus_id=pending["campus_id"],
                start_at=datetime.fromisoformat(pending["start_at"]), duration_minutes=pending["duration_minutes"],
            )
        except (ScheduleConflictError, ValueError) as exc:
            return {"category": "scheduling", "status": "conflict", "answer": str(exc)}
        if booking.student_id is not None:
            self.repository.set_student_preferred_teacher(booking.student_id, teacher_id)
        self.session_store.reset(session_id)
        return {
            "category": "scheduling", "status": "confirmed",
            "answer": f"排课成功：{teacher_name}，课程安排 #{booking.id}。",
            "booking": {"id": booking.id, "teacher_id": teacher_id, "teacher_name": teacher_name, "start_at": self._iso_business_time(booking.start_at), "status": booking.status},
        }

    @staticmethod
    def _iso_business_time(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo("UTC"))
        return value.astimezone(ZoneInfo("Asia/Shanghai")).isoformat()
