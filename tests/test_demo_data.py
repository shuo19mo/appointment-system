from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app import seed_demo_data
from services.scheduling_service import SchedulingService


SHANGHAI = ZoneInfo("Asia/Shanghai")
REFERENCE_TIME = datetime(2026, 8, 28, 10, 0, tzinfo=SHANGHAI)


def test_demo_seed_builds_a_repeatable_multi_campus_operation(repository):
    seed_demo_data(repository, reference_time=REFERENCE_TIME)
    seed_demo_data(repository, reference_time=REFERENCE_TIME)

    assert len(repository.list_campuses()) == 5
    assert len(repository.list_teachers()) == 15
    assert len(repository.list_courses()) == 10
    assert len(repository.list_students()) == 18
    assert len(repository.list_bookings()) == 12
    assert len(repository.list_knowledge()) == 12
    assert {booking.status for booking in repository.list_bookings()} == {
        "cancelled",
        "confirmed",
        "pending",
    }
    wang = repository.find_teacher("王老师")
    assert len(repository.list_teacher_availability(wang.id)) == 14


def test_demo_seed_contains_a_preferred_teacher_conflict_with_alternatives(repository):
    seed_demo_data(repository, reference_time=REFERENCE_TIME)
    service = SchedulingService(repository)
    start_at = (REFERENCE_TIME + timedelta(days=1)).replace(hour=14, minute=0)

    candidates = service.match_teachers(
        student_id=repository.find_student("小明").id,
        course_id=repository.find_course("数学", "初二").id,
        campus_id=repository.find_campus("浦东校区").id,
        start_at=start_at,
        duration_minutes=90,
        preferred_teacher_id=repository.find_teacher("王老师").id,
    )

    assert candidates
    assert "王老师" not in {candidate.teacher.name for candidate in candidates}
    assert all(candidate.preferred_teacher_unavailable for candidate in candidates)


def test_demo_seed_contains_a_teacher_daily_load_limit_scenario(repository):
    seed_demo_data(repository, reference_time=REFERENCE_TIME)
    service = SchedulingService(repository)
    start_at = (REFERENCE_TIME + timedelta(days=3)).replace(hour=10, minute=0)

    candidates = service.match_teachers(
        student_id=repository.find_student("小明").id,
        course_id=repository.find_course("数学", "高一").id,
        campus_id=repository.find_campus("静安校区").id,
        start_at=start_at,
        duration_minutes=90,
        preferred_teacher_id=repository.find_teacher("周老师").id,
    )

    assert candidates
    assert "周老师" not in {candidate.teacher.name for candidate in candidates}
    assert "高老师" in {candidate.teacher.name for candidate in candidates}
