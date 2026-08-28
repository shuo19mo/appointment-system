"""FastAPI entry point for the multi-campus education scheduling agent."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from agents.coordinator import EducationCoordinator
from agents.llm.runtime import create_deepseek_runtime
from agents.session_store import SessionStore
from api import api_routers
from db.db_router import DatabaseRouter
from config.agent import AgentSettings
from config.model_provider import create_local_embedding_provider
from db.demo_data import seed_demo_data
from web import router as web_router


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def create_app(
    *, repository=None, initialize_demo: bool = False, initialize_schema: bool = False,
    llm_runtime=None, embedding_provider=None,
) -> FastAPI:
    database_router = None
    if repository is None:
        database_router = DatabaseRouter(
            os.getenv("DATABASE_URL", "sqlite:///data/education_scheduling.db"),
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
            initialize_schema=initialize_schema or initialize_demo,
        )
        repository = database_router.education
    if initialize_demo:
        seed_demo_data(repository)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        if application.state.llm_runtime is None:
            application.state.llm_runtime = create_deepseek_runtime(AgentSettings.from_env())
        if application.state.embedding_provider is None:
            application.state.embedding_provider = create_local_embedding_provider()
        if application.state.coordinator is None:
            application.state.coordinator = EducationCoordinator(
                repository,
                application.state.session_store,
                llm_runtime=application.state.llm_runtime,
                embedding_provider=application.state.embedding_provider,
            )
        yield

    app = FastAPI(title="多校区智能排课 AI Agent", description="补习机构教师匹配、排课与课程咨询服务", version="2.0.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.state.repository = repository
    app.state.database_router = database_router
    session_store = SessionStore(ttl_seconds=int(os.getenv("SESSION_TTL_SECONDS", "1800")))
    app.state.session_store = session_store
    app.state.llm_runtime = llm_runtime
    app.state.embedding_provider = embedding_provider
    app.state.coordinator = (
        EducationCoordinator(
            repository,
            session_store,
            llm_runtime=llm_runtime,
            embedding_provider=embedding_provider,
        )
        if llm_runtime is not None
        else None
    )
    for router in api_routers:
        app.include_router(router)
    app.include_router(web_router)
    app.mount("/static", StaticFiles(directory=ROOT / "web" / "static"), name="static")

    @app.get("/health", tags=["系统"])
    def health():
        return {"status": "ok", "service": "education-scheduling-agent"}

    @app.get("/ready", tags=["系统"])
    def ready():
        coordinator = app.state.coordinator
        runtime = app.state.llm_runtime
        if coordinator is None or runtime is None or not coordinator.consultant.ready:
            from fastapi import HTTPException

            raise HTTPException(503, "Agent 尚未就绪")
        return {"status": "ready", "agent_mode": "llm", "model": runtime.model_name}

    return app


app = create_app(
    initialize_schema=os.getenv("AUTO_INIT_DB", "false").lower() == "true",
    initialize_demo=os.getenv("SEED_DEMO_DATA", "false").lower() == "true",
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
