from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import subprocess
import sys
from threading import Barrier
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
import pytest

from app import create_app
from db.db_router import DatabaseRouter
from db.repositories.education_repository import RepositoryConflict


SHANGHAI = ZoneInfo("Asia/Shanghai")


def test_cross_offset_round_trip_and_conflict(repository, seeded):
    start = datetime(2026, 9, 5, 10, 0, tzinfo=SHANGHAI)
    repository.create_booking(
        student_id=seeded["student"].id,
        teacher_id=seeded["wang"].id,
        course_id=seeded["course"].id,
        campus_id=seeded["campus"].id,
        start_at=start,
        end_at=start + timedelta(minutes=90),
    )

    same_instant_overlap = datetime(2026, 9, 5, 2, 30, tzinfo=timezone.utc)
    assert repository.has_teacher_conflict(
        seeded["wang"].id,
        same_instant_overlap,
        same_instant_overlap + timedelta(minutes=30),
    )
    stored = repository.list_bookings()[0]
    assert stored.start_at.tzinfo is not None
    assert stored.start_at.astimezone(timezone.utc) == datetime(
        2026, 9, 5, 2, 0, tzinfo=timezone.utc
    )


def test_concurrent_booking_creation_serializes_sqlite_writes(tmp_path):
    database = tmp_path / "concurrent.db"
    router = DatabaseRouter(f"sqlite:///{database}", initialize_schema=True)
    repository = router.education
    campus = repository.create_campus("并发校区", "测试地址")
    course = repository.create_course("并发数学", "数学", "初二")
    student = repository.create_student("并发学生", "初二")
    teacher = repository.create_teacher("并发老师")
    start = datetime(2026, 9, 5, 10, 0, tzinfo=SHANGHAI)
    barrier = Barrier(8)

    def create_once(index):
        barrier.wait()
        try:
            booking = repository.create_booking_checked(
                student_id=student.id,
                teacher_id=teacher.id,
                course_id=course.id,
                campus_id=campus.id,
                start_at=start,
                end_at=start + timedelta(minutes=90),
                notes=str(index),
            )
            return ("created", booking.id)
        except RepositoryConflict as exc:
            return ("conflict", exc.resource)

    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(create_once, range(8)))
        assert [item[0] for item in results].count("created") == 1
        assert [item[0] for item in results].count("conflict") == 7
        assert len(repository.list_bookings()) == 1
    finally:
        router.close()


def test_create_schedule_requires_student(repository, seeded):
    client = TestClient(create_app(repository=repository, initialize_demo=False))
    response = client.post(
        "/api/schedules",
        json={
            "teacher_id": seeded["wang"].id,
            "course_id": seeded["course"].id,
            "campus_id": seeded["campus"].id,
            "start_at": "2026-09-05T14:00:00+08:00",
            "duration_minutes": 90,
        },
    )
    assert response.status_code == 422


def test_management_crud_relationships_and_knowledge_contract(repository):
    client = TestClient(create_app(repository=repository, initialize_demo=False))
    campus = client.post("/api/campuses", json={"name": "静安校区", "address": "南京西路 1 号"})
    course = client.post(
        "/api/courses",
        json={"name": "高二物理", "subject": "物理", "grade": "高二", "duration_minutes": 120},
    )
    teacher = client.post("/api/teachers", json={"name": "陈老师", "specialties": "高中物理"})
    student = client.post("/api/students", json={"name": "小华", "grade": "高二", "contact": "13900000000"})
    assert {campus.status_code, course.status_code, teacher.status_code, student.status_code} == {201}

    teacher_id = teacher.json()["id"]
    course_id = course.json()["id"]
    campus_id = campus.json()["id"]
    assert client.post(f"/api/teachers/{teacher_id}/courses/{course_id}").status_code == 201
    assert client.post(f"/api/teachers/{teacher_id}/campuses/{campus_id}").status_code == 201
    availability = client.post(
        f"/api/teachers/{teacher_id}/availability",
        json={"start_at": "2026-09-06T09:00:00+08:00", "end_at": "2026-09-06T18:00:00+08:00"},
    )
    assert availability.status_code == 201
    assert availability.json()["start_at"].endswith("+08:00")

    updated = client.put(f"/api/teachers/{teacher_id}", json={"bio": "物理教研组长"})
    assert updated.status_code == 200
    assert updated.json()["bio"] == "物理教研组长"

    knowledge = client.post(
        "/api/knowledge",
        json={"content": "静安校区提供高中物理课程。", "category": "campus", "keywords": ["静安"]},
    )
    assert knowledge.status_code == 201
    listed = client.get("/api/knowledge")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["content"] == "静安校区提供高中物理课程。"

    assert client.delete(f"/api/teachers/{teacher_id}/availability/{availability.json()['id']}").status_code == 200
    assert client.delete(f"/api/students/{student.json()['id']}").status_code == 200


def test_invalid_chat_time_returns_422(repository, seeded):
    client = TestClient(create_app(repository=repository, initialize_demo=False))
    response = client.post(
        "/api/chat",
        json={"session_id": "bad-time", "message": "给小明在浦东校区约初二数学，2026-02-30 14:00，90分钟"},
    )
    assert response.status_code == 422
    assert "时间" in response.json()["detail"]


def test_importing_app_does_not_create_or_seed_database(tmp_path):
    database = tmp_path / "import-side-effect.db"
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": f"sqlite:///{database}",
            "AUTO_INIT_DB": "false",
            "SEED_DEMO_DATA": "false",
            "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
        }
    )
    result = subprocess.run(
        [sys.executable, "-c", "import app"],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert not database.exists()


def test_sqlite_foreign_keys_are_enabled(tmp_path):
    router = DatabaseRouter(f"sqlite:///{tmp_path / 'foreign-keys.db'}", initialize_schema=True)
    try:
        with router.engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
    finally:
        router.close()
