import sys
from types import SimpleNamespace

import pytest

from agents.llm.runtime import DeepSeekLLMRuntime
from agents.task_classification_agent import TaskRoute
from app import create_app
from config.agent import AgentConfigurationError, AgentSettings
from config.model_provider import create_deepseek_chat_model
from tests.fakes import FakeEmbeddingProvider, FakeLLMRuntime


def test_agent_settings_require_deepseek_key(monkeypatch):
    monkeypatch.setenv("AGENT_MODE", "llm")
    monkeypatch.setenv("MODEL_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(AgentConfigurationError, match="DEEPSEEK_API_KEY"):
        AgentSettings.from_env()


def test_agent_settings_reject_non_llm_mode(monkeypatch):
    monkeypatch.setenv("AGENT_MODE", "rules")
    monkeypatch.setenv("MODEL_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")

    with pytest.raises(AgentConfigurationError, match="AGENT_MODE"):
        AgentSettings.from_env()


def test_agent_settings_use_current_deepseek_defaults(monkeypatch):
    monkeypatch.setenv("AGENT_MODE", "llm")
    monkeypatch.setenv("MODEL_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    settings = AgentSettings.from_env()

    assert settings.base_url == "https://api.deepseek.com"
    assert settings.model == "deepseek-v4-flash"


def test_deepseek_model_disables_default_thinking_mode_for_agent_tools(monkeypatch):
    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            self.extra_body = kwargs.get("extra_body")

    monkeypatch.setitem(sys.modules, "langchain_openai", SimpleNamespace(ChatOpenAI=FakeChatOpenAI))

    model = create_deepseek_chat_model(AgentSettings(api_key="test-key"))

    assert model.extra_body == {"thinking": {"type": "disabled"}}


def test_structured_output_uses_deepseek_compatible_function_calling():
    class StructuredRunnable:
        def invoke(self, messages):
            return {"category": "unsupported"}

    class FunctionCallingOnlyModel:
        def with_structured_output(self, schema, *, method):
            if method != "function_calling":
                raise RuntimeError("DeepSeek V4 does not support this structured-output method")
            return StructuredRunnable()

    runtime = DeepSeekLLMRuntime(
        AgentSettings(api_key="test-key"),
        chat_model=FunctionCallingOnlyModel(),
    )

    result = runtime.structured(system="route", user="weather", schema=TaskRoute)

    assert result == TaskRoute(category="unsupported")


def test_app_accepts_injected_fake_runtime(repository):
    runtime = FakeLLMRuntime()
    embedding = FakeEmbeddingProvider()

    application = create_app(
        repository=repository,
        llm_runtime=runtime,
        embedding_provider=embedding,
    )

    assert application.state.llm_runtime is runtime
    assert application.state.embedding_provider is embedding
