"""Education knowledge retrieval with an offline keyword baseline.

Semantic retrieval can be added through ``config.model_provider`` without
changing the consultation-agent interface. Live schedules never enter this
knowledge index; they are queried through ``SchedulingService``.
"""


class KnowledgeService:
    def __init__(self, repository):
        self.repository = repository

    def search(self, query: str, *, top_k: int = 3, category: str | None = None):
        return self.repository.search_knowledge(query, category=category, limit=top_k)

    def add_document(self, content: str, category: str, keywords: list[str] | None = None):
        return self.repository.add_knowledge(content, category, keywords)
