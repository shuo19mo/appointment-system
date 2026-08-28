#!/usr/bin/env python3
"""Offline smoke test for the education scheduling environment."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


CORE_PACKAGES = (
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("jinja2", "jinja2"),
    ("multipart", "python-multipart"),
    ("pydantic", "pydantic"),
    ("sqlalchemy", "sqlalchemy"),
    ("dotenv", "python-dotenv"),
    ("aiofiles", "aiofiles"),
)


def main() -> int:
    project_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(project_root))
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    if sys.version_info < (3, 11):
        print("FAIL Python 3.11+ is required")
        return 1

    failures = []
    for module, label in CORE_PACKAGES:
        try:
            importlib.import_module(module)
            print(f"OK   {label}")
        except Exception as exc:
            failures.append(label)
            print(f"FAIL {label}: {exc}")
    if failures:
        return 1

    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        from app import create_app
        from db.models import Base
        from db.repositories.education_repository import EducationRepository

        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        repository = EducationRepository(sessionmaker(bind=engine, expire_on_commit=False))
        application = create_app(repository=repository, initialize_demo=False)
        health_route = next(route for route in application.routes if route.path == "/health")
        assert health_route.endpoint()["service"] == "education-scheduling-agent"
        print("OK   app import and /health")
    except Exception as exc:
        print(f"FAIL application smoke test: {exc}")
        return 1

    print("Optional AI keys are not required for core mode.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
