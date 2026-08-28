from agents.task_classification_agent import TaskClassificationAgent
from tests.fakes import FakeLLMRuntime


def test_classifier_uses_llm_structured_result():
    runtime = FakeLLMRuntime(structured={"TaskRoute": [{"category": "scheduling"}]})
    classifier = TaskClassificationAgent(runtime)

    assert classifier.classify("帮我处理一下", {"student_name": "小明"}) == "scheduling"
    assert runtime.structured_calls[0]["schema"] == "TaskRoute"
    assert "student_name" in runtime.structured_calls[0]["user"]


def test_classifier_returns_each_bounded_route():
    runtime = FakeLLMRuntime(
        structured={
            "TaskRoute": [
                {"category": "consultation"},
                {"category": "unsupported"},
            ]
        }
    )
    classifier = TaskClassificationAgent(runtime)

    assert classifier.classify("课程适合谁", {}) == "consultation"
    assert classifier.classify("今天天气", {}) == "unsupported"
