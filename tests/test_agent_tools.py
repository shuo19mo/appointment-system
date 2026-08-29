from collections import deque

from langchain_core.messages import AIMessage
from pydantic import BaseModel

from agents.coordinator import EducationCoordinator
from agents.education_tools import EducationTools, MatchTeachersArgs
from agents.llm.runtime import DeepSeekLLMRuntime
from agents.llm.tools import AgentTool
from agents.session_store import SessionStore
from config.agent import AgentSettings
from tests.fakes import FakeEmbeddingProvider, FakeLLMRuntime


def test_education_tools_return_real_teacher_candidates(repository, seeded):
    tools = EducationTools(repository)

    result = tools.match_teachers(
        MatchTeachersArgs(
            student_id=seeded["student"].id,
            course_id=seeded["course"].id,
            campus_id=seeded["campus"].id,
            start_at="2026-09-05T14:00:00+08:00",
            duration_minutes=90,
            preferred_teacher_id=seeded["wang"].id,
        )
    )

    assert result["candidates"][0]["teacher_name"] == "王老师"
    assert isinstance(result["candidates"][0]["teacher_id"], int)


def test_lookup_tools_return_json_safe_records(repository, seeded):
    tools = EducationTools(repository)

    assert tools.lookup_student({"name": "小明"})["student"]["id"] == seeded["student"].id
    assert tools.lookup_campus({"name": "浦东校区"})["campus"]["name"] == "浦东校区"
    assert tools.lookup_course({"subject": "数学", "grade": "初二"})["course"]["name"] == "初二数学提升"


def test_teacher_course_tool_lists_qualified_teachers(repository, seeded):
    tools = EducationTools(repository)
    teacher_tool = {tool.name: tool for tool in tools.registry()}.get("list_teachers_for_course")

    assert teacher_tool is not None
    result = teacher_tool.handler({"subject": "数学", "grade": "初二"})

    assert result["course"]["name"] == "初二数学提升"
    assert [teacher["name"] for teacher in result["teachers"]] == ["王老师", "李老师"]


def test_model_cannot_create_booking_without_server_confirmation(repository, seeded):
    runtime = FakeLLMRuntime(
        structured={
            "TaskRoute": [{"category": "scheduling"}],
            "SchedulingExtraction": [{"action": "confirm", "preferred_teacher_name": "王老师"}],
        }
    )
    coordinator = EducationCoordinator(
        repository,
        SessionStore(),
        llm_runtime=runtime,
        embedding_provider=FakeEmbeddingProvider(),
    )

    result = coordinator.process("family", "直接帮我下单")

    assert result["status"] != "confirmed"
    assert repository.list_bookings() == []
    assert "create_booking" not in coordinator.available_tool_names


def test_registered_tools_are_read_only(repository):
    registry = EducationTools(repository).registry()

    assert "match_teachers" in {tool.name for tool in registry}
    assert all("create_booking" not in tool.name for tool in registry)


class _LookupArgs(BaseModel):
    name: str


class _BoundChatModel:
    def __init__(self):
        self.responses = deque(
            [
                AIMessage(content="", tool_calls=[{"name": "lookup", "args": {"name": "小明"}, "id": "call-1"}]),
                AIMessage(content="查询完成"),
            ]
        )
        self.invocations = 0

    def bind_tools(self, tools):
        self.bound_tools = tools
        return self

    def invoke(self, messages):
        self.invocations += 1
        return self.responses.popleft()


def test_deepseek_runtime_executes_bounded_tool_loop_without_leaking_args():
    model = _BoundChatModel()
    runtime = DeepSeekLLMRuntime(AgentSettings(api_key="test"), chat_model=model)
    tool = AgentTool("lookup", "测试查询", _LookupArgs, lambda args: {"name": args.name})

    result = runtime.tool_loop(system="system", user="query", tools=[tool], max_steps=4)

    assert result.answer == "查询完成"
    assert result.trace == ("lookup: success",)
    assert "小明" not in " ".join(result.trace)
    assert model.invocations == 2
