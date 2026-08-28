"""FastAPI entry point for the multi-campus education scheduling agent."""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

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
from web import router as web_router


ROOT = Path(__file__).resolve().parent
SHANGHAI = ZoneInfo("Asia/Shanghai")
load_dotenv(ROOT / ".env")


def seed_demo_data(repository) -> None:
    if repository.list_campuses():
        return
    pudong = repository.create_campus("浦东校区", "上海市浦东新区张江路 88 号")
    xuhui = repository.create_campus("徐汇校区", "上海市徐汇区漕溪北路 120 号")
    math = repository.create_course("初二数学提升", "数学", "初二", 90, "代数、几何与校内同步提升")
    english = repository.create_course("高一英语强化", "英语", "高一", 90, "阅读、语法与写作综合训练")
    student = repository.create_student("小明", "初二", "13800000000")
    wang = repository.create_teacher("王老师", "八年初中数学教学经验", "初中数学、几何")
    li = repository.create_teacher("李老师", "擅长分层教学与学习规划", "初中数学、高中英语")
    zhang = repository.create_teacher("张老师", "高中英语教研教师", "高中英语、写作")
    for teacher, courses, campuses in ((wang, (math,), (pudong,)), (li, (math, english), (pudong, xuhui)), (zhang, (english,), (xuhui,))):
        for course in courses:
            repository.qualify_teacher(teacher.id, course.id)
        for campus in campuses:
            repository.assign_teacher_to_campus(teacher.id, campus.id)
        today = datetime.now(SHANGHAI).replace(hour=9, minute=0, second=0, microsecond=0)
        for day in range(30):
            start = today + timedelta(days=day)
            repository.add_teacher_availability(teacher.id, start, start.replace(hour=21))
    repository.add_knowledge("浦东校区位于张江路 88 号，提供初中数学一对一课程。", "campus", ["浦东校区", "地址"])
    repository.add_knowledge("课程开始前 24 小时可免费取消或改期；不足 24 小时请联系教务协调。", "policy", ["取消", "改期", "政策"])
    repository.add_knowledge("初二数学提升课覆盖代数、几何和校内同步复习，默认每次 90 分钟。", "course", ["初二", "数学", "课程"])


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
        if application.state.coordinator is None:
            application.state.coordinator = EducationCoordinator(repository, application.state.session_store)
        yield

    app = FastAPI(title="多校区智能排课 AI Agent", description="补习机构教师匹配、排课与课程咨询服务", version="2.0.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.state.repository = repository
    app.state.database_router = database_router
    session_store = SessionStore(ttl_seconds=int(os.getenv("SESSION_TTL_SECONDS", "1800")))
    app.state.session_store = session_store
    app.state.llm_runtime = llm_runtime
    app.state.embedding_provider = embedding_provider
    app.state.coordinator = EducationCoordinator(repository, session_store) if llm_runtime is not None else None
    for router in api_routers:
        app.include_router(router)
    app.include_router(web_router)
    app.mount("/static", StaticFiles(directory=ROOT / "web" / "static"), name="static")

    @app.get("/health", tags=["系统"])
    def health():
        return {"status": "ok", "service": "education-scheduling-agent"}

    return app


app = create_app(
    initialize_schema=os.getenv("AUTO_INIT_DB", "false").lower() == "true",
    initialize_demo=os.getenv("SEED_DEMO_DATA", "false").lower() == "true",
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
