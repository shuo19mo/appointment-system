"""FastAPI endpoints for education scheduling and consultation."""

from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from agents.llm.runtime import LLMUnavailableError
from services.scheduling_service import ScheduleConflictError, SchedulingService, SchedulingValidationError


router = APIRouter(prefix="/api", tags=["教育排课"])


class MatchRequest(BaseModel):
    student_id: int | None = None
    course_id: int
    campus_id: int
    start_at: datetime
    duration_minutes: int = Field(default=90, gt=0, le=360)
    preferred_teacher_id: int | None = None


class CreateScheduleRequest(MatchRequest):
    student_id: int
    teacher_id: int
    notes: str = ""


class CampusCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=255)


class CampusUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = Field(default=None, min_length=1, max_length=255)


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    subject: str = Field(min_length=1, max_length=50)
    grade: str = Field(min_length=1, max_length=50)
    duration_minutes: int = Field(default=90, gt=0, le=360)
    description: str = ""


class CourseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    subject: str | None = Field(default=None, min_length=1, max_length=50)
    grade: str | None = Field(default=None, min_length=1, max_length=50)
    duration_minutes: int | None = Field(default=None, gt=0, le=360)
    description: str | None = None


class TeacherCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    bio: str = ""
    specialties: str = ""


class TeacherUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    bio: str | None = None
    specialties: str | None = None
    max_daily_minutes: int | None = Field(default=None, gt=0, le=1440)


class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    grade: str = Field(min_length=1, max_length=50)
    contact: str = Field(default="", max_length=100)


class StudentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    grade: str | None = Field(default=None, min_length=1, max_length=50)
    contact: str | None = Field(default=None, max_length=100)


class AvailabilityRequest(BaseModel):
    start_at: datetime
    end_at: datetime


class KnowledgeRequest(BaseModel):
    content: str = Field(min_length=1)
    category: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None


def _repository(request: Request):
    return request.app.state.repository


def _business_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))
    return value.astimezone(ZoneInfo("Asia/Shanghai")).isoformat()


def _write_or_conflict(action):
    try:
        return action()
    except IntegrityError as exc:
        raise HTTPException(409, "记录重复或关联资源不存在") from exc


def _validate_match_resources(repository, payload: MatchRequest, *, teacher_id: int | None = None) -> None:
    if repository.get_course(payload.course_id) is None:
        raise HTTPException(404, "课程不存在")
    if repository.get_campus(payload.campus_id) is None:
        raise HTTPException(404, "校区不存在")
    if payload.student_id is not None and repository.get_student(payload.student_id) is None:
        raise HTTPException(404, "学生不存在")
    if payload.preferred_teacher_id is not None and repository.get_teacher(payload.preferred_teacher_id) is None:
        raise HTTPException(404, "偏好教师不存在")
    if teacher_id is not None and repository.get_teacher(teacher_id) is None:
        raise HTTPException(404, "教师不存在")


def _booking_json(booking):
    return {
        "id": booking.id,
        "student_id": booking.student_id,
        "teacher_id": booking.teacher_id,
        "course_id": booking.course_id,
        "campus_id": booking.campus_id,
        "start_at": _business_iso(booking.start_at),
        "end_at": _business_iso(booking.end_at),
        "status": booking.status,
        "notes": booking.notes,
    }


@router.get("/campuses")
def list_campuses(request: Request):
    return [{"id": item.id, "name": item.name, "address": item.address} for item in _repository(request).list_campuses()]


@router.post("/campuses", status_code=status.HTTP_201_CREATED)
def create_campus(payload: CampusCreate, request: Request):
    item = _write_or_conflict(lambda: _repository(request).create_campus(payload.name, payload.address))
    return {"id": item.id, "name": item.name, "address": item.address}


@router.put("/campuses/{campus_id}")
def update_campus(campus_id: int, payload: CampusUpdate, request: Request):
    item = _write_or_conflict(lambda: _repository(request).update_campus(campus_id, **payload.model_dump(exclude_none=True)))
    if item is None:
        raise HTTPException(404, "校区不存在")
    return {"id": item.id, "name": item.name, "address": item.address}


@router.delete("/campuses/{campus_id}")
def delete_campus(campus_id: int, request: Request):
    if _repository(request).deactivate_campus(campus_id) is None:
        raise HTTPException(404, "校区不存在")
    return {"status": "deactivated", "id": campus_id}


@router.get("/courses")
def list_courses(request: Request):
    return [{"id": item.id, "name": item.name, "subject": item.subject, "grade": item.grade, "duration_minutes": item.duration_minutes, "description": item.description} for item in _repository(request).list_courses()]


@router.post("/courses", status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, request: Request):
    item = _write_or_conflict(lambda: _repository(request).create_course(**payload.model_dump()))
    return {"id": item.id, **payload.model_dump()}


@router.put("/courses/{course_id}")
def update_course(course_id: int, payload: CourseUpdate, request: Request):
    item = _write_or_conflict(lambda: _repository(request).update_course(course_id, **payload.model_dump(exclude_none=True)))
    if item is None:
        raise HTTPException(404, "课程不存在")
    return {"id": item.id, "name": item.name, "subject": item.subject, "grade": item.grade, "duration_minutes": item.duration_minutes, "description": item.description}


@router.delete("/courses/{course_id}")
def delete_course(course_id: int, request: Request):
    if _repository(request).deactivate_course(course_id) is None:
        raise HTTPException(404, "课程不存在")
    return {"status": "deactivated", "id": course_id}


@router.get("/teachers")
def list_teachers(request: Request):
    return [{"id": item.id, "name": item.name, "bio": item.bio, "specialties": item.specialties} for item in _repository(request).list_teachers()]


@router.post("/teachers", status_code=status.HTTP_201_CREATED)
def create_teacher(payload: TeacherCreate, request: Request):
    item = _write_or_conflict(lambda: _repository(request).create_teacher(**payload.model_dump()))
    return {"id": item.id, "name": item.name, "bio": item.bio, "specialties": item.specialties}


@router.put("/teachers/{teacher_id}")
def update_teacher(teacher_id: int, payload: TeacherUpdate, request: Request):
    item = _write_or_conflict(lambda: _repository(request).update_teacher(teacher_id, **payload.model_dump(exclude_none=True)))
    if item is None:
        raise HTTPException(404, "教师不存在")
    return {"id": item.id, "name": item.name, "bio": item.bio, "specialties": item.specialties, "max_daily_minutes": item.max_daily_minutes}


@router.delete("/teachers/{teacher_id}")
def delete_teacher(teacher_id: int, request: Request):
    if _repository(request).deactivate_teacher(teacher_id) is None:
        raise HTTPException(404, "教师不存在")
    return {"status": "deactivated", "id": teacher_id}


@router.get("/students")
def list_students(request: Request):
    return [{"id": item.id, "name": item.name, "grade": item.grade, "contact": item.contact} for item in _repository(request).list_students()]


@router.post("/students", status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate, request: Request):
    item = _write_or_conflict(lambda: _repository(request).create_student(**payload.model_dump()))
    return {"id": item.id, "name": item.name, "grade": item.grade, "contact": item.contact}


@router.put("/students/{student_id}")
def update_student(student_id: int, payload: StudentUpdate, request: Request):
    item = _repository(request).update_student(student_id, **payload.model_dump(exclude_none=True))
    if item is None:
        raise HTTPException(404, "学生不存在")
    return {"id": item.id, "name": item.name, "grade": item.grade, "contact": item.contact}


@router.delete("/students/{student_id}")
def delete_student(student_id: int, request: Request):
    if _repository(request).deactivate_student(student_id) is None:
        raise HTTPException(404, "学生不存在")
    return {"status": "deactivated", "id": student_id}


@router.post("/teachers/{teacher_id}/courses/{course_id}", status_code=status.HTTP_201_CREATED)
def add_teacher_course(teacher_id: int, course_id: int, request: Request):
    repository = _repository(request)
    if repository.get_teacher(teacher_id) is None or repository.get_course(course_id) is None:
        raise HTTPException(404, "教师或课程不存在")
    item = _write_or_conflict(lambda: repository.qualify_teacher(teacher_id, course_id))
    return {"id": item.id, "teacher_id": teacher_id, "course_id": course_id}


@router.delete("/teachers/{teacher_id}/courses/{course_id}")
def delete_teacher_course(teacher_id: int, course_id: int, request: Request):
    if not _repository(request).remove_teacher_course(teacher_id, course_id):
        raise HTTPException(404, "授课资格不存在")
    return {"status": "deleted"}


@router.post("/teachers/{teacher_id}/campuses/{campus_id}", status_code=status.HTTP_201_CREATED)
def add_teacher_campus(teacher_id: int, campus_id: int, request: Request):
    repository = _repository(request)
    if repository.get_teacher(teacher_id) is None or repository.get_campus(campus_id) is None:
        raise HTTPException(404, "教师或校区不存在")
    item = _write_or_conflict(lambda: repository.assign_teacher_to_campus(teacher_id, campus_id))
    return {"id": item.id, "teacher_id": teacher_id, "campus_id": campus_id}


@router.delete("/teachers/{teacher_id}/campuses/{campus_id}")
def delete_teacher_campus(teacher_id: int, campus_id: int, request: Request):
    if not _repository(request).remove_teacher_campus(teacher_id, campus_id):
        raise HTTPException(404, "教师校区关联不存在")
    return {"status": "deleted"}


@router.get("/teachers/{teacher_id}/availability")
def teacher_availability(teacher_id: int, request: Request):
    if _repository(request).get_teacher(teacher_id) is None:
        raise HTTPException(404, "教师不存在")
    return [{"id": item.id, "start_at": _business_iso(item.start_at), "end_at": _business_iso(item.end_at)} for item in _repository(request).list_teacher_availability(teacher_id)]


@router.post("/teachers/{teacher_id}/availability", status_code=status.HTTP_201_CREATED)
def add_teacher_availability(teacher_id: int, payload: AvailabilityRequest, request: Request):
    repository = _repository(request)
    if repository.get_teacher(teacher_id) is None:
        raise HTTPException(404, "教师不存在")
    try:
        item = repository.add_teacher_availability(teacher_id, payload.start_at, payload.end_at)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"id": item.id, "teacher_id": teacher_id, "start_at": _business_iso(item.start_at), "end_at": _business_iso(item.end_at)}


@router.delete("/teachers/{teacher_id}/availability/{availability_id}")
def delete_teacher_availability(teacher_id: int, availability_id: int, request: Request):
    if not _repository(request).remove_teacher_availability(teacher_id, availability_id):
        raise HTTPException(404, "教师档期不存在")
    return {"status": "deleted"}


@router.post("/schedules/match")
def match_teachers(payload: MatchRequest, request: Request):
    repository = _repository(request)
    _validate_match_resources(repository, payload)
    service = SchedulingService(repository)
    try:
        candidates = service.match_teachers(**payload.model_dump())
    except SchedulingValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"candidates": [{"teacher_id": item.teacher.id, "teacher_name": item.teacher.name, "score": item.score, "reasons": list(item.reasons), "preferred_teacher_unavailable": item.preferred_teacher_unavailable} for item in candidates]}


@router.post("/schedules", status_code=status.HTTP_201_CREATED)
def create_schedule(payload: CreateScheduleRequest, request: Request):
    repository = _repository(request)
    _validate_match_resources(repository, payload, teacher_id=payload.teacher_id)
    values = payload.model_dump(exclude={"preferred_teacher_id"})
    try:
        booking = SchedulingService(repository).create_booking(**values)
    except ScheduleConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except SchedulingValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    return _booking_json(booking)


@router.get("/schedules")
def list_schedules(request: Request, student_id: int | None = None, teacher_id: int | None = None):
    bookings = _repository(request).list_bookings(student_id=student_id, teacher_id=teacher_id)
    return [{**_booking_json(item), "student_name": item.student.name if item.student else None, "teacher_name": item.teacher.name, "course_name": item.course.name, "campus_name": item.campus.name} for item in bookings]


@router.delete("/schedules/{booking_id}")
def cancel_schedule(booking_id: int, request: Request):
    booking = _repository(request).cancel_booking(booking_id)
    if booking is None:
        raise HTTPException(404, "课程安排不存在")
    return _booking_json(booking)


@router.post("/knowledge", status_code=status.HTTP_201_CREATED)
def add_knowledge(payload: KnowledgeRequest, request: Request):
    item = _repository(request).add_knowledge(payload.content, payload.category, payload.keywords)
    return {"id": item.id, "content": item.content, "category": item.category, "keywords": item.keywords}


@router.get("/knowledge")
def list_knowledge(request: Request, category: str | None = None, limit: int = 100):
    items = _repository(request).list_knowledge(category, limit)
    return {"items": [{"id": item.id, "content": item.content, "category": item.category, "keywords": item.keywords} for item in items]}


@router.get("/knowledge/search")
def search_knowledge(request: Request, q: str, category: str | None = None, limit: int = 5):
    coordinator = request.app.state.coordinator
    if coordinator is None:
        raise HTTPException(503, "Agent 尚未就绪")
    results = coordinator.consultant.knowledge.search(q, top_k=limit, category=category)
    return {"results": [{"id": item.id, "content": item.content, "category": item.category, "score": item.score} for item in results]}


@router.post("/chat")
def chat(payload: ChatRequest, request: Request):
    session_id = payload.session_id or str(uuid4())
    request_id = str(uuid4())
    try:
        result = request.app.state.coordinator.process(session_id, payload.message)
    except LLMUnavailableError as exc:
        raise HTTPException(503, "DeepSeek 服务暂时不可用") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"session_id": session_id, "request_id": request_id, **result}
