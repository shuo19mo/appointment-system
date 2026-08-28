from agents.consultant_agent import ConsultantAgent
from agents.llm.runtime import ToolLoopResult
from services.knowledge_service import VectorKnowledgeService
from tests.fakes import FakeEmbeddingProvider, FakeLLMRuntime


def test_vector_service_ranks_semantic_match(repository):
    repository.add_knowledge("课程开始前24小时可以免费取消。", "policy", ["取消"])
    repository.add_knowledge("浦东校区位于张江路。", "campus", ["地址"])
    service = VectorKnowledgeService(repository, FakeEmbeddingProvider())

    hits = service.search("临时有事怎么退课", top_k=1)

    assert hits[0].category == "policy"
    assert "24小时" in hits[0].content


def test_vector_index_rebuilds_when_documents_change(repository):
    repository.add_knowledge("浦东校区位于张江路。", "campus", ["地址"])
    service = VectorKnowledgeService(repository, FakeEmbeddingProvider())
    assert service.search("退课", top_k=1)[0].category == "campus"

    repository.add_knowledge("临时有事可按取消政策处理。", "policy", ["取消"])

    assert service.search("怎么退课", top_k=1)[0].category == "policy"


def test_consultant_uses_search_tool_and_returns_sources(repository):
    repository.add_knowledge("课程开始前24小时可以免费取消。", "policy", ["取消"])
    runtime = FakeLLMRuntime(
        tool_answer="可提前24小时取消",
        tool_plan=[("search_knowledge", {"query": "临时有事怎么退课", "top_k": 3})],
    )
    agent = ConsultantAgent(repository, runtime, FakeEmbeddingProvider())

    result = agent.process("怎么取消课程")

    assert result["answer"] == "可提前24小时取消"
    assert result["sources"][0]["category"] == "policy"
    assert result["tool_trace"] == ["search_knowledge: success"]
    assert runtime.tool_calls[0]["tools"] == ["search_knowledge"]


def test_consultant_does_not_invent_sources_when_model_skips_tool(repository):
    runtime = FakeLLMRuntime(tool_results=[ToolLoopResult(answer="没有依据", trace=())])
    agent = ConsultantAgent(repository, runtime, FakeEmbeddingProvider())

    result = agent.process("未知政策")

    assert result["sources"] == []
    assert result["answer"] == "暂时没有检索到足够资料，请联系教务老师进一步确认。"
