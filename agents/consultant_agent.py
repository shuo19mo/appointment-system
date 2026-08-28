"""Offline-first consultation agent backed by education knowledge documents."""

from db.repositories.education_repository import EducationRepository
from services.knowledge_service import KnowledgeService


class ConsultantAgent:
    def __init__(self, repository: EducationRepository):
        self.repository = repository
        self.knowledge = KnowledgeService(repository)

    def process(self, question: str) -> dict:
        documents = self.knowledge.search(question, top_k=3)
        if not documents:
            return {
                "category": "consultation",
                "answer": "暂时没有检索到相关课程或校区资料，请联系教务老师进一步确认。",
                "sources": [],
            }
        answer = "\n".join(f"- {document.content}" for document in documents)
        return {
            "category": "consultation",
            "answer": answer,
            "sources": [{"id": item.id, "category": item.category} for item in documents],
        }
