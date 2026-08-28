"""Factories for the mandatory DeepSeek chat model and local embeddings."""

from __future__ import annotations

from pydantic import SecretStr

from config.agent import AgentSettings


def create_deepseek_chat_model(settings: AgentSettings, *, temperature: float = 0):
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.model,
        api_key=SecretStr(settings.api_key),
        base_url=settings.base_url,
        temperature=temperature,
        timeout=settings.timeout_seconds,
        max_retries=settings.max_retries,
        extra_body={"thinking": {"type": "disabled"}},
    )


def create_local_embedding_provider(model_name: str = "BAAI/bge-small-zh-v1.5"):
    from sentence_transformers import SentenceTransformer

    class SentenceTransformerEmbeddingProvider:
        def __init__(self):
            self.model = SentenceTransformer(model_name)

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return self.model.encode(texts).tolist()

        def embed_query(self, text: str) -> list[float]:
            return self.model.encode([text])[0].tolist()

    return SentenceTransformerEmbeddingProvider()
