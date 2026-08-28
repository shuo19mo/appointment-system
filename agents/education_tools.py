"""Read-only education tools exposed to the LLM Agent."""

from datetime import datetime

from pydantic import BaseModel, Field

from agents.llm.tools import AgentTool
from services.scheduling_service import SchedulingService


class NameLookupArgs(BaseModel):
    name: str = Field(min_length=1)


class CourseLookupArgs(BaseModel):
    subject: str = Field(min_length=1)
    grade: str = Field(min_length=1)


class MatchTeachersArgs(BaseModel):
    student_id: int | None = None
    course_id: int
    campus_id: int
    start_at: datetime
    duration_minutes: int = Field(gt=0, le=360)
    preferred_teacher_id: int | None = None


class SearchKnowledgeArgs(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)
    category: str | None = None


class EducationTools:
    def __init__(self, repository):
        self.repository = repository
        self.scheduling = SchedulingService(repository)

    @staticmethod
    def _args(schema: type[BaseModel], value) -> BaseModel:
        return value if isinstance(value, schema) else schema.model_validate(value)

    def lookup_student(self, args) -> dict:
        parsed = self._args(NameLookupArgs, args)
        item = self.repository.find_student(parsed.name)
        return {"student": None if item is None else {"id": item.id, "name": item.name, "grade": item.grade}}

    def lookup_campus(self, args) -> dict:
        parsed = self._args(NameLookupArgs, args)
        item = self.repository.find_campus(parsed.name)
        return {"campus": None if item is None else {"id": item.id, "name": item.name, "address": item.address}}

    def lookup_course(self, args) -> dict:
        parsed = self._args(CourseLookupArgs, args)
        item = self.repository.find_course(parsed.subject, parsed.grade)
        return {
            "course": None if item is None else {
                "id": item.id, "name": item.name, "subject": item.subject, "grade": item.grade,
                "duration_minutes": item.duration_minutes, "description": item.description,
            }
        }

    def lookup_teacher(self, args) -> dict:
        parsed = self._args(NameLookupArgs, args)
        item = self.repository.find_teacher(parsed.name)
        return {
            "teacher": None if item is None else {
                "id": item.id, "name": item.name, "bio": item.bio, "specialties": item.specialties,
            }
        }

    def match_teachers(self, args) -> dict:
        parsed = self._args(MatchTeachersArgs, args)
        candidates = self.scheduling.match_teachers(**parsed.model_dump())
        return {
            "candidates": [
                {
                    "teacher_id": item.teacher.id,
                    "teacher_name": item.teacher.name,
                    "score": item.score,
                    "reasons": list(item.reasons),
                    "preferred_teacher_unavailable": item.preferred_teacher_unavailable,
                }
                for item in candidates
            ]
        }

    def registry(self) -> list[AgentTool]:
        return [
            AgentTool("lookup_student", "按姓名查询学生基础资料，不返回联系方式。", NameLookupArgs, self.lookup_student),
            AgentTool("lookup_campus", "按名称查询校区与地址。", NameLookupArgs, self.lookup_campus),
            AgentTool("lookup_course", "按学科和年级查询课程。", CourseLookupArgs, self.lookup_course),
            AgentTool("lookup_teacher", "按姓名查询教师简介与专长。", NameLookupArgs, self.lookup_teacher),
            AgentTool("match_teachers", "按真实课程、校区、时间和资质查询可选教师。", MatchTeachersArgs, self.match_teachers),
        ]
