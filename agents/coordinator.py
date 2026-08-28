"""Top-level DeepSeek education Agent coordinator."""

from agents.consultant_agent import ConsultantAgent
from agents.llm.runtime import LLMRuntime
from agents.scheduling_agent import SchedulingAgent
from agents.session_store import SessionStore
from agents.task_classification_agent import TaskClassificationAgent


class EducationCoordinator:
    def __init__(self, repository, session_store: SessionStore | None = None, *, llm_runtime: LLMRuntime, embedding_provider=None):
        self.sessions = session_store or SessionStore()
        self.runtime = llm_runtime
        self.classifier = TaskClassificationAgent(llm_runtime)
        self.scheduling = SchedulingAgent(repository, self.sessions, llm_runtime)
        self.consultant = ConsultantAgent(repository)

    @property
    def available_tool_names(self) -> list[str]:
        return []

    def process(self, session_id: str, message: str) -> dict:
        category = self.classifier.classify(message, self.sessions.get(session_id))
        if category == "scheduling":
            result = self.scheduling.process(session_id, message)
        elif category == "consultation":
            result = self.consultant.process(message)
        else:
            result = {"category": "unrelated", "answer": "我可以帮助安排一对一课程，或解答课程、教师、校区和机构政策问题。"}
        return {**result, "agent_mode": "llm", "model": self.runtime.model_name, "tool_trace": result.get("tool_trace", [])}
