import pytest

from app import create_app
from config.agent import AgentConfigurationError, AgentSettings
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
