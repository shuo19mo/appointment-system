from datetime import datetime
from zoneinfo import ZoneInfo

from agents.coordinator import EducationCoordinator
from tests.fakes import FakeEmbeddingProvider, FakeLLMRuntime


def _coordinator(repository, structured):
    runtime = FakeLLMRuntime(structured=structured)
    return EducationCoordinator(
        repository,
        llm_runtime=runtime,
        embedding_provider=FakeEmbeddingProvider(),
    ), runtime


def test_chat_matches_then_confirms_booking(repository, seeded):
    coordinator, runtime = _coordinator(
        repository,
        {
            "TaskRoute": [{"category": "scheduling"}, {"category": "scheduling"}],
            "SchedulingExtraction": [
                {
                    "action": "schedule",
                    "student_name": "小明",
                    "campus_name": "浦东校区",
                    "subject": "数学",
                    "grade": "初二",
                    "start_at": "2026-09-05T14:00:00+08:00",
                    "duration_minutes": 90,
                    "preferred_teacher_name": "王老师",
                },
                {"action": "confirm", "preferred_teacher_name": "王老师"},
            ],
        },
    )

    matched = coordinator.process("family-1", "帮我安排")
    confirmed = coordinator.process("family-1", "就这个")

    assert matched["status"] == "matched"
    assert confirmed["status"] == "confirmed"
    assert confirmed["booking"]["teacher_name"] == "王老师"
    assert len(repository.list_bookings()) == 1
    assert confirmed["agent_mode"] == "llm"
    assert confirmed["model"] == "fake-deepseek"
    assert len(runtime.structured_calls) == 4


def test_model_cannot_confirm_without_pending_proposal(repository, seeded):
    coordinator, _ = _coordinator(
        repository,
        {
            "TaskRoute": [{"category": "scheduling"}],
            "SchedulingExtraction": [{"action": "confirm", "preferred_teacher_name": "王老师"}],
        },
    )

    result = coordinator.process("new-session", "确认")

    assert result["status"] == "missing_context"
    assert repository.list_bookings() == []


def test_chat_can_cancel_booking_by_llm_action(repository, service, seeded):
    booking = service.create_booking(
        student_id=seeded["student"].id,
        teacher_id=seeded["wang"].id,
        course_id=seeded["course"].id,
        campus_id=seeded["campus"].id,
        start_at=datetime(2026, 9, 5, 14, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        duration_minutes=90,
    )
    coordinator, _ = _coordinator(
        repository,
        {
            "TaskRoute": [{"category": "scheduling"}],
            "SchedulingExtraction": [{"action": "cancel", "booking_id": booking.id}],
        },
    )

    result = coordinator.process("family-1", "不要了")

    assert result["status"] == "cancelled"
    assert repository.list_bookings()[0].status == "cancelled"


def test_chat_explicit_duration_overrides_previous_turn(repository, seeded):
    coordinator, _ = _coordinator(
        repository,
        {
            "TaskRoute": [
                {"category": "scheduling"},
                {"category": "scheduling"},
                {"category": "scheduling"},
            ],
            "SchedulingExtraction": [
                {
                    "action": "schedule", "student_name": "小明", "campus_name": "浦东校区",
                    "subject": "数学", "grade": "初二", "start_at": "2026-09-05T14:00:00+08:00",
                    "duration_minutes": 60,
                },
                {"action": "schedule", "duration_minutes": 90},
                {"action": "confirm", "preferred_teacher_name": "王老师"},
            ],
        },
    )

    assert coordinator.process("family-duration", "先约一下")["status"] == "matched"
    assert coordinator.process("family-duration", "换个时长")["status"] == "matched"
    confirmed = coordinator.process("family-duration", "可以了")

    booking = repository.list_bookings()[0]
    assert confirmed["status"] == "confirmed"
    assert (booking.end_at - booking.start_at).total_seconds() == 90 * 60


def test_chat_reports_unknown_preferred_teacher(repository, seeded):
    coordinator, _ = _coordinator(
        repository,
        {
            "TaskRoute": [{"category": "scheduling"}],
            "SchedulingExtraction": [{
                "action": "schedule", "student_name": "小明", "campus_name": "浦东校区",
                "subject": "数学", "grade": "初二", "start_at": "2026-09-05T14:00:00+08:00",
                "preferred_teacher_name": "赵老师",
            }],
        },
    )

    result = coordinator.process("family-teacher", "请处理")

    assert result["status"] == "not_found"
    assert "教师" in result["answer"]
