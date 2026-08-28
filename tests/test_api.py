from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app import create_app


def test_health_and_education_homepage(repository, seeded):
    client = TestClient(create_app(repository=repository, initialize_demo=False))

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "service": "education-scheduling-agent"}

    homepage = client.get("/")
    assert homepage.status_code == 200
    assert "智能排课" in homepage.text
    assert "多校区" in homepage.text


def test_match_and_create_schedule_api(repository, seeded):
    client = TestClient(create_app(repository=repository, initialize_demo=False))
    start = datetime(2026, 9, 5, 14, 0, tzinfo=ZoneInfo("Asia/Shanghai")).isoformat()
    payload = {
        "student_id": seeded["student"].id,
        "course_id": seeded["course"].id,
        "campus_id": seeded["campus"].id,
        "start_at": start,
        "duration_minutes": 90,
        "preferred_teacher_id": seeded["wang"].id,
    }

    matched = client.post("/api/schedules/match", json=payload)
    assert matched.status_code == 200
    assert matched.json()["candidates"][0]["teacher_name"] == "王老师"

    created = client.post(
        "/api/schedules",
        json={**payload, "teacher_id": seeded["wang"].id},
    )
    assert created.status_code == 201
    assert created.json()["status"] == "confirmed"
    assert created.json()["start_at"].endswith("+08:00")

    conflict = client.post(
        "/api/schedules",
        json={**payload, "teacher_id": seeded["wang"].id},
    )
    assert conflict.status_code == 409


def test_knowledge_search_uses_education_content(repository, seeded):
    repository.add_knowledge(
        content="浦东校区允许开课前24小时免费取消课程。",
        category="policy",
        keywords=["取消", "浦东校区"],
    )
    client = TestClient(create_app(repository=repository, initialize_demo=False))

    response = client.get("/api/knowledge/search", params={"q": "浦东校区怎么取消课程"})

    assert response.status_code == 200
    assert response.json()["results"][0]["category"] == "policy"
    assert "24小时" in response.json()["results"][0]["content"]


def test_match_rejects_unknown_course(repository, seeded):
    client = TestClient(create_app(repository=repository, initialize_demo=False))
    response = client.post(
        "/api/schedules/match",
        json={
            "student_id": seeded["student"].id,
            "course_id": 9999,
            "campus_id": seeded["campus"].id,
            "start_at": "2026-09-05T14:00:00+08:00",
            "duration_minutes": 90,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "课程不存在"
