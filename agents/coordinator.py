"""Top-level education agent coordinator."""

from agents.consultant_agent import ConsultantAgent
from agents.scheduling_agent import SchedulingAgent
from agents.session_store import SessionStore
from agents.task_classification_agent import TaskClassificationAgent


class EducationCoordinator:
    def __init__(self, repository, session_store: SessionStore | None = None):
        self.sessions = session_store or SessionStore()
        self.classifier = TaskClassificationAgent()
        self.scheduling = SchedulingAgent(repository, self.sessions)
        self.consultant = ConsultantAgent(repository)

    def process(self, session_id: str, message: str) -> dict:
        category = self.classifier.classify(message)
        if category == "scheduling":
            return self.scheduling.process(session_id, message)
        if category == "consultation":
            return self.consultant.process(message)
        return {"category": "unrelated", "answer": "我可以帮助安排一对一课程，或解答课程、教师、校区和机构政策问题。"}
