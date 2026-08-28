"""Grounded DeepSeek consultation Agent backed by FAISS retrieval."""

from agents.education_tools import SearchKnowledgeArgs
from agents.llm.runtime import LLMRuntime
from agents.llm.tools import AgentTool
from services.knowledge_service import VectorKnowledgeService


class ConsultantAgent:
    def __init__(self, repository, runtime: LLMRuntime, embedding_provider):
        self.runtime = runtime
        self.knowledge = VectorKnowledgeService(repository, embedding_provider)

    @property
    def ready(self) -> bool:
        return self.knowledge.ready

    def process(self, question: str) -> dict:
        collected_sources: list[dict] = []

        def search_knowledge(args: SearchKnowledgeArgs) -> dict:
            hits = self.knowledge.search(args.query, top_k=args.top_k, category=args.category)
            for hit in hits:
                collected_sources.append({"id": hit.id, "category": hit.category})
            return {
                "results": [
                    {"id": hit.id, "content": hit.content, "category": hit.category, "score": hit.score}
                    for hit in hits
                ]
            }

        result = self.runtime.tool_loop(
            system=("你是补习机构课程顾问 Agent。回答前必须调用 search_knowledge。"
                    "只能依据工具返回的资料回答；资料不足时明确说无法确认，不得编造价格、师资或政策。"),
            user=(question or "").strip(),
            tools=[AgentTool("search_knowledge", "检索机构课程、教师、校区和政策资料。", SearchKnowledgeArgs, search_knowledge)],
            max_steps=4,
        )
        seen = set()
        sources = []
        for source in collected_sources:
            key = (source["id"], source["category"])
            if key not in seen:
                seen.add(key)
                sources.append(source)
        grounded_answer = result.answer if sources else "暂时没有检索到足够资料，请联系教务老师进一步确认。"
        return {
            "category": "consultation",
            "answer": grounded_answer,
            "sources": sources,
            "tool_trace": list(result.trace),
        }
