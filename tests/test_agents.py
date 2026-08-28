from datetime import datetime
from zoneinfo import ZoneInfo

from agents.coordinator import EducationCoordinator


def test_chat_matches_then_confirms_booking(repository, seeded):
    coordinator = EducationCoordinator(repository)

    matched = coordinator.process(
        "family-1",
        "给小明在浦东校区约初二数学，2026-09-05 14:00，90分钟，最好王老师",
    )
    assert matched["status"] == "matched"
    assert matched["candidates"][0]["teacher_name"] == "王老师"

    confirmed = coordinator.process("family-1", "确认王老师")
    assert confirmed["status"] == "confirmed"
    assert confirmed["booking"]["teacher_name"] == "王老师"
    assert len(repository.list_bookings()) == 1


def test_chat_can_cancel_booking_by_id(repository, service, seeded):
    booking = service.create_booking(
        student_id=seeded["student"].id,
        teacher_id=seeded["wang"].id,
        course_id=seeded["course"].id,
        campus_id=seeded["campus"].id,
        start_at=datetime(2026, 9, 5, 14, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        duration_minutes=90,
    )
    coordinator = EducationCoordinator(repository)

    result = coordinator.process("family-1", f"取消课程 {booking.id}")

    assert result["status"] == "cancelled"
    assert repository.list_bookings()[0].status == "cancelled"


def test_chat_explicit_duration_overrides_previous_turn(repository, seeded):
    coordinator = EducationCoordinator(repository)
    first = coordinator.process(
        "family-duration",
        "给小明在浦东校区约初二数学，2026-09-05 14:00，60分钟",
    )
    assert first["status"] == "matched"

    second = coordinator.process("family-duration", "改成90分钟")

    assert second["status"] == "matched"
    confirmed = coordinator.process("family-duration", "确认王老师")
    booking = repository.list_bookings()[0]
    assert confirmed["status"] == "confirmed"
    assert (booking.end_at - booking.start_at).total_seconds() == 90 * 60


def test_chat_reports_unknown_preferred_teacher(repository, seeded):
    coordinator = EducationCoordinator(repository)

    result = coordinator.process(
        "family-teacher",
        "给小明在浦东校区约初二数学，2026-09-05 14:00，最好赵老师",
    )

    assert result["status"] == "not_found"
    assert "教师" in result["answer"]
