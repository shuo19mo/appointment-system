from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_single_dependency_path_contains_mandatory_agent_stack():
    requirements = _read("requirements.txt")

    assert not (ROOT / "requirements-ai.txt").exists()
    for dependency in ("langchain-core", "langchain-openai", "faiss-cpu", "sentence-transformers"):
        assert dependency in requirements


def test_environment_example_declares_mandatory_deepseek_runtime():
    example = _read(".env.example")

    assert "AGENT_MODE=llm" in example
    assert "MODEL_PROVIDER=deepseek" in example
    assert "DEEPSEEK_API_KEY=" in example
    assert "LLM_MODEL=deepseek-v4-flash" in example


def test_docs_and_project_skills_do_not_claim_rule_fallback():
    paths = (
        "README.md",
        "DEV_SPEC.md",
        ".github/skills/setup-environment/SKILL.md",
        ".github/skills/interview-prep/SKILL.md",
        ".github/skills/interview-prep/references/project_knowledge.md",
        ".github/skills/project-learner/SKILL.md",
        ".github/skills/project-learner/references/knowledge_map.md",
        ".github/skills/resume-writer/SKILL.md",
        ".github/skills/resume-writer/references/project_highlights.md",
    )
    source = "\n".join(_read(path) for path in paths)
    forbidden = (
        "AI 可选", "可选 AI", "规则降级", "离线关键词分类", "离线中文字段解析",
        "无模型 key 可运行", "requirements-ai.txt", "关键词检索基线",
    )

    assert not any(term in source for term in forbidden)
    assert "DeepSeek" in source
    assert "FAISS" in source


def test_setup_verifier_requires_key_and_checks_readiness():
    verifier = _read(".github/skills/setup-environment/scripts/verify_env.py")

    assert "DEEPSEEK_API_KEY" in verifier
    assert 'route.path == "/ready"' in verifier
