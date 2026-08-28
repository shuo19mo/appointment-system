#!/usr/bin/env python3
"""Network-free smoke test for the mandatory DeepSeek Agent environment."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


REQUIRED_PACKAGES = (
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("jinja2", "jinja2"),
    ("multipart", "python-multipart"),
    ("pydantic", "pydantic"),
    ("sqlalchemy", "sqlalchemy"),
    ("dotenv", "python-dotenv"),
    ("aiofiles", "aiofiles"),
    ("langchain_core", "langchain-core"),
    ("langchain_openai", "langchain-openai"),
    ("faiss", "faiss-cpu"),
    ("numpy", "numpy"),
    ("sentence_transformers", "sentence-transformers"),
)


class _SmokeRuntime:
    def __init__(self, model_name: str):
        self.model_name = model_name


class _SmokeEmbeddingProvider:
    def embed_documents(self, texts):
        return [[1.0, 0.0] for _ in texts]

    def embed_query(self, text):
        return [1.0, 0.0]


def main() -> int:
    project_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(project_root))
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    if sys.version_info < (3, 11):
        print("FAIL Python 3.11+ is required")
        return 1

    failures = []
    for module, label in REQUIRED_PACKAGES:
        try:
            importlib.import_module(module)
            print(f"OK   {label}")
        except Exception as exc:
            failures.append(label)
            print(f"FAIL {label}: {exc}")
    if failures:
        return 1

    try:
        from dotenv import load_dotenv

        load_dotenv(project_root / ".env")
        from config.agent import AgentSettings

        settings = AgentSettings.from_env()
        print(f"OK   mandatory DeepSeek config ({settings.model})")
    except Exception as exc:
        print(f"FAIL DeepSeek configuration: {exc}")
        print("Set AGENT_MODE=llm, MODEL_PROVIDER=deepseek, and DEEPSEEK_API_KEY in .env.")
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
        application = create_app(
            repository=repository,
            initialize_demo=False,
            llm_runtime=_SmokeRuntime(settings.model),
            embedding_provider=_SmokeEmbeddingProvider(),
        )
        health_route = next(route for route in application.routes if route.path == "/health")
        ready_route = next(route for route in application.routes if route.path == "/ready")
        assert health_route.endpoint()["service"] == "education-scheduling-agent"
        assert ready_route.endpoint()["agent_mode"] == "llm"
        print("OK   app import, /health, and /ready")
    except Exception as exc:
        print(f"FAIL application smoke test: {exc}")
        return 1

    print("DeepSeek Agent environment is ready; no paid model request was sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
