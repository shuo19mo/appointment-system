from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.models import Base
from db.repositories.education_repository import EducationRepository
from services.scheduling_service import SchedulingService


SHANGHAI = ZoneInfo("Asia/Shanghai")


@pytest.fixture
def repository():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return EducationRepository(factory)


@pytest.fixture
def seeded(repository):
    campus = repository.create_campus("浦东校区", "上海市浦东新区")
    course = repository.create_course(
        name="初二数学提升",
        subject="数学",
        grade="初二",
        duration_minutes=90,
        description="聚焦代数、几何和校内同步提升",
    )
    student = repository.create_student("小明", "初二", "13800000000")
    wang = repository.create_teacher("王老师", "数学教研组长", "初中数学、几何")
    li = repository.create_teacher("李老师", "耐心细致", "初中数学、代数")

    for teacher in (wang, li):
        repository.qualify_teacher(teacher.id, course.id)
        repository.assign_teacher_to_campus(teacher.id, campus.id)
        repository.add_teacher_availability(
            teacher.id,
            datetime(2026, 9, 5, 9, 0, tzinfo=SHANGHAI),
            datetime(2026, 9, 5, 20, 0, tzinfo=SHANGHAI),
        )

    return {
        "campus": campus,
        "course": course,
        "student": student,
        "wang": wang,
        "li": li,
    }


@pytest.fixture
def service(repository):
    return SchedulingService(repository)
