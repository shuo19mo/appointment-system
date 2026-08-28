from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from services.scheduling_service import ScheduleConflictError


SHANGHAI = ZoneInfo("Asia/Shanghai")


def test_preferred_teacher_conflict_returns_available_alternative(service, repository, seeded):
    start = datetime(2026, 9, 5, 14, 0, tzinfo=SHANGHAI)
    repository.create_booking(
        student_id=seeded["student"].id,
        teacher_id=seeded["wang"].id,
        course_id=seeded["course"].id,
        campus_id=seeded["campus"].id,
        start_at=start,
        end_at=start.replace(hour=15, minute=30),
    )

    candidates = service.match_teachers(
        student_id=None,
        course_id=seeded["course"].id,
        campus_id=seeded["campus"].id,
        start_at=start,
        duration_minutes=90,
        preferred_teacher_id=seeded["wang"].id,
    )

    assert [candidate.teacher.name for candidate in candidates] == ["李老师"]
    assert candidates[0].preferred_teacher_unavailable is True


def test_booking_blocks_teacher_and_student_overlap_but_allows_adjacent(service, repository, seeded):
    start = datetime(2026, 9, 5, 14, 0, tzinfo=SHANGHAI)
    booking = service.create_booking(
        student_id=seeded["student"].id,
        teacher_id=seeded["wang"].id,
        course_id=seeded["course"].id,
        campus_id=seeded["campus"].id,
        start_at=start,
        duration_minutes=90,
    )
    assert booking.status == "confirmed"

    another_student = repository.create_student("小红", "初二")

    with pytest.raises(ScheduleConflictError, match="教师"):
        service.create_booking(
            student_id=another_student.id,
            teacher_id=seeded["wang"].id,
            course_id=seeded["course"].id,
            campus_id=seeded["campus"].id,
            start_at=start.replace(hour=15),
            duration_minutes=90,
        )

    with pytest.raises(ScheduleConflictError, match="学生"):
        service.create_booking(
            student_id=seeded["student"].id,
            teacher_id=seeded["li"].id,
            course_id=seeded["course"].id,
            campus_id=seeded["campus"].id,
            start_at=start.replace(hour=15),
            duration_minutes=90,
        )

    adjacent = service.create_booking(
        student_id=seeded["student"].id,
        teacher_id=seeded["li"].id,
        course_id=seeded["course"].id,
        campus_id=seeded["campus"].id,
        start_at=start.replace(hour=15, minute=30),
        duration_minutes=90,
    )
    adjacent_business_time = adjacent.start_at.astimezone(SHANGHAI)
    assert adjacent_business_time.hour == 15
    assert adjacent_business_time.minute == 30


def test_match_is_deterministic_and_prefers_requested_teacher(service, seeded):
    candidates = service.match_teachers(
        student_id=seeded["student"].id,
        course_id=seeded["course"].id,
        campus_id=seeded["campus"].id,
        start_at=datetime(2026, 9, 5, 10, 0, tzinfo=SHANGHAI),
        duration_minutes=90,
        preferred_teacher_id=seeded["li"].id,
    )

    assert [item.teacher.name for item in candidates] == ["李老师", "王老师"]
    assert candidates[0].score > candidates[1].score


def test_student_history_preference_adds_soft_ranking_score(service, repository, seeded):
    repository.set_student_preferred_teacher(seeded["student"].id, seeded["li"].id)

    candidates = service.match_teachers(
        student_id=seeded["student"].id,
        course_id=seeded["course"].id,
        campus_id=seeded["campus"].id,
        start_at=datetime(2026, 9, 5, 10, 0, tzinfo=SHANGHAI),
        duration_minutes=90,
    )

    assert candidates[0].teacher.name == "李老师"
    assert "学生历史偏好" in candidates[0].reasons
    assert candidates[0].score - candidates[1].score == 15
