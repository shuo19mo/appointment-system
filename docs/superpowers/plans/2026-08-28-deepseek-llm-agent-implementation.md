# Mandatory DeepSeek LLM Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the rule-driven chat path with a mandatory DeepSeek multi-Agent runtime while preserving deterministic scheduling safety and offline automated tests.

**Architecture:** A DeepSeek runtime adapter supplies strict structured output and a bounded tool loop to router, scheduling, and consultation Agents. Read tools call the existing repository and scheduling service; write actions remain behind server-side confirmation and always re-enter `SchedulingService`. FAISS retrieval uses an injected local embedding provider so tests can use deterministic fakes.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2, LangChain Core/OpenAI, DeepSeek OpenAI-compatible API, FAISS, sentence-transformers, pytest.

**Spec:** `docs/superpowers/specs/2026-08-28-deepseek-llm-agent-design.md`

## Global Constraints

- Production chat has only `AGENT_MODE=llm`; no keyword or regex fallback may be called.
- `MODEL_PROVIDER=deepseek` and non-empty `DEEPSEEK_API_KEY` are mandatory at application startup.
- Default model is configurable and set to `deepseek-v4-flash`; base URL defaults to `https://api.deepseek.com`.
- LLM output never writes directly to the repository; confirmed writes go through `SchedulingService`.
- Prompts, API keys, raw Chain-of-Thought, and full private user text are not included in API traces or logs.
- Default tests use fake model and embedding providers and make no network calls.
- Existing UTC persistence, Shanghai API serialization, SQLite `BEGIN IMMEDIATE`, and 27 regression tests remain green.

---

### Task 1: Mandatory DeepSeek runtime and application startup contract

**Files:**
- Create: `config/agent.py`
- Create: `agents/llm/__init__.py`
- Create: `agents/llm/runtime.py`
- Create: `tests/fakes.py`
- Create: `tests/test_llm_runtime.py`
- Modify: `config/model_provider.py`
- Modify: `app.py`
- Modify: `tests/conftest.py`

**Interfaces:**
- Produces: `AgentSettings.from_env() -> AgentSettings`, `DeepSeekLLMRuntime`, `LLMRuntime` protocol, `ToolLoopResult`, `AgentConfigurationError`, `LLMUnavailableError`.
- Produces: `create_app(..., llm_runtime: LLMRuntime | None = None, embedding_provider=None)`; injected runtimes bypass production credential creation for tests.
- Consumes: existing `EducationRepository`, `SessionStore`, and `EducationCoordinator` constructor, which Task 2 will update.

- [ ] **Step 1: Write failing configuration and startup tests**

```python
def test_agent_settings_require_deepseek_key(monkeypatch):
    monkeypatch.setenv("AGENT_MODE", "llm")
    monkeypatch.setenv("MODEL_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(AgentConfigurationError, match="DEEPSEEK_API_KEY"):
        AgentSettings.from_env()


def test_app_accepts_injected_fake_runtime(repository):
    runtime = FakeLLMRuntime()
    application = create_app(repository=repository, llm_runtime=runtime, embedding_provider=FakeEmbeddingProvider())
    assert application.state.llm_runtime is runtime
```

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv/bin/pytest -q tests/test_llm_runtime.py`

Expected: collection fails because `config.agent`, `agents.llm.runtime`, and `FakeLLMRuntime` do not exist.

- [ ] **Step 3: Implement settings and runtime interfaces**

```python
@dataclass(frozen=True)
class AgentSettings:
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    timeout_seconds: float = 30.0
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> "AgentSettings":
        if os.getenv("AGENT_MODE") != "llm":
            raise AgentConfigurationError("AGENT_MODE must be llm")
        if os.getenv("MODEL_PROVIDER") != "deepseek":
            raise AgentConfigurationError("MODEL_PROVIDER must be deepseek")
        key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not key:
            raise AgentConfigurationError("DEEPSEEK_API_KEY is required")
        return cls(api_key=key, base_url=os.getenv("LLM_BASE_URL", cls.base_url), model=os.getenv("LLM_MODEL", cls.model))
```

Define `LLMRuntime` with:

```python
class LLMRuntime(Protocol):
    model_name: str
    def structured(self, *, system: str, user: str, schema: type[BaseModel]) -> BaseModel: ...
    def text(self, *, system: str, user: str) -> str: ...
    def tool_loop(self, *, system: str, user: str, tools: list[AgentTool], max_steps: int = 4) -> ToolLoopResult: ...
```

`DeepSeekLLMRuntime` creates `ChatOpenAI(model=settings.model, api_key=SecretStr(settings.api_key), base_url=settings.base_url, timeout=settings.timeout_seconds, max_retries=settings.max_retries)` and wraps provider exceptions as `LLMUnavailableError("DeepSeek 服务暂时不可用")` without including upstream bodies.

- [ ] **Step 4: Add a startup lifespan that constructs mandatory production dependencies**

```python
@asynccontextmanager
async def lifespan(application):
    if application.state.llm_runtime is None:
        application.state.llm_runtime = create_deepseek_runtime(AgentSettings.from_env())
    application.state.coordinator = EducationCoordinator(
        application.state.repository,
        application.state.session_store,
        llm_runtime=application.state.llm_runtime,
        embedding_provider=application.state.embedding_provider,
    )
    yield
```

When a fake runtime is injected, construct the coordinator eagerly so existing `TestClient` usage remains deterministic. Do not validate credentials at module import; production Uvicorn fails during startup lifespan instead.

- [ ] **Step 5: Run focused and baseline tests**

Run: `.venv/bin/pytest -q tests/test_llm_runtime.py tests/test_api.py::test_health_and_education_homepage`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add config/agent.py config/model_provider.py agents/llm tests/fakes.py tests/test_llm_runtime.py tests/conftest.py app.py
git commit -m "feat: require DeepSeek agent runtime"
```

---

### Task 2: LLM task router and structured scheduling extraction

**Files:**
- Modify: `agents/task_classification_agent.py`
- Replace: `agents/scheduling/input_parser.py`
- Modify: `agents/scheduling/models.py`
- Modify: `agents/scheduling_agent.py`
- Modify: `agents/coordinator.py`
- Modify: `tests/test_task_classification.py`
- Modify: `tests/test_parser.py`
- Modify: `tests/test_agents.py`
- Create: `tests/test_no_rule_fallback.py`

**Interfaces:**
- Consumes: `LLMRuntime.structured`, `SessionStore`, `SchedulingRequestData`.
- Produces: `TaskClassificationAgent(runtime).classify(text, session_state) -> str` and `LLMSchedulingInputParser(runtime).parse(text, current_state) -> SchedulingRequestData`.
- Produces: every chat result includes `agent_mode="llm"`, `model`, and a bounded `tool_trace` list.

- [ ] **Step 1: Replace rule-oriented tests with Fake LLM behavior tests**

```python
def test_classifier_uses_llm_structured_result():
    runtime = FakeLLMRuntime(structured={"TaskRoute": [{"category": "scheduling"}]})
    classifier = TaskClassificationAgent(runtime)
    assert classifier.classify("帮我处理一下", {}) == "scheduling"
    assert runtime.structured_calls[0]["schema"] == "TaskRoute"


def test_parser_merges_only_fields_provided_by_llm():
    runtime = FakeLLMRuntime(structured={"SchedulingExtraction": [{"action": "schedule", "duration_minutes": 90}]})
    parser = LLMSchedulingInputParser(runtime)
    result = parser.parse("改成九十分钟", {"student_name": "小明", "duration_minutes": 60})
    assert result.student_name == "小明"
    assert result.duration_minutes == 90
    assert result.provided_fields == {"duration_minutes"}


def test_production_chat_path_has_no_rule_fallback():
    forbidden = ("SCHEDULING_TERMS", "CONSULTATION_TERMS", "_parse_relative_time")
    paths = [Path("agents/task_classification_agent.py"), Path("agents/scheduling/input_parser.py")]
    source = "\n".join(path.read_text() for path in paths)
    assert not any(term in source for term in forbidden)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv/bin/pytest -q tests/test_task_classification.py tests/test_parser.py tests/test_no_rule_fallback.py`

Expected: FAIL because constructors do not accept `LLMRuntime` and the parser still uses regex.

- [ ] **Step 3: Implement strict router and extraction schemas**

```python
class TaskRoute(BaseModel):
    category: Literal["scheduling", "consultation", "unsupported"]


class SchedulingExtraction(BaseModel):
    action: Literal["schedule", "confirm", "cancel"] = "schedule"
    booking_id: int | None = None
    student_name: str | None = None
    campus_name: str | None = None
    subject: str | None = None
    grade: str | None = None
    start_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=360)
    preferred_teacher_name: str | None = None
```

The parser sends the current Shanghai timestamp, prior JSON state, and latest message to `runtime.structured`. It derives `provided_fields` from non-`None` scheduling fields, merges only those fields over current state, and defaults duration to 90 only when no current or extracted duration exists. `action` and `booking_id` are control fields and are not merged into appointment details. Delete all regex constants, keyword tables, and relative-time parsing from the production parser.

- [ ] **Step 4: Inject runtime through coordinator and scheduling Agent**

```python
class EducationCoordinator:
    def __init__(self, repository, session_store, *, llm_runtime, embedding_provider):
        self.classifier = TaskClassificationAgent(llm_runtime)
        self.scheduling = SchedulingAgent(repository, session_store, llm_runtime)
        self.consultant = ConsultantAgent(repository, llm_runtime, embedding_provider)
```

Use existing session state when routing. Confirmation and cancellation are selected from the LLM's structured `action`, but execution remains server-controlled: confirmation requires an existing pending proposal, and cancellation requires a real booking ID owned by the current session workflow. Remove pre-LLM keyword/regex branches. Add response metadata without exposing prompts or model reasoning.

- [ ] **Step 5: Run Agent tests**

Run: `.venv/bin/pytest -q tests/test_task_classification.py tests/test_parser.py tests/test_agents.py tests/test_no_rule_fallback.py`

Expected: PASS and Fake runtime call records prove the LLM path was used.

- [ ] **Step 6: Commit**

```bash
git add agents/coordinator.py agents/task_classification_agent.py agents/scheduling agents/scheduling_agent.py tests/test_task_classification.py tests/test_parser.py tests/test_agents.py tests/test_no_rule_fallback.py
git commit -m "feat: route and extract scheduling requests with DeepSeek"
```

---

### Task 3: Bounded Agent tool loop and booking confirmation gate

**Files:**
- Create: `agents/llm/tools.py`
- Create: `agents/education_tools.py`
- Modify: `agents/llm/runtime.py`
- Modify: `agents/scheduling_agent.py`
- Create: `tests/test_agent_tools.py`
- Modify: `tests/test_agents.py`

**Interfaces:**
- Consumes: `EducationRepository`, `SchedulingService`, `LLMRuntime.tool_loop`.
- Produces: `AgentTool(name, description, args_schema, handler)`, `EducationTools.lookup_*`, `EducationTools.match_teachers`, `ToolTrace`.
- Enforces: no registered ordinary tool directly calls `create_booking`; confirmation continues through `_confirm_pending_booking`.

- [ ] **Step 1: Write failing lookup/tool-loop and confirmation safety tests**

```python
def test_education_tools_return_real_teacher_candidates(repository, seeded):
    tools = EducationTools(repository)
    result = tools.match_teachers(MatchTeachersArgs(
        student_id=seeded["student"].id,
        course_id=seeded["course"].id,
        campus_id=seeded["campus"].id,
        start_at="2026-09-05T14:00:00+08:00",
        duration_minutes=90,
    ))
    assert result["candidates"][0]["teacher_name"] == "王老师"


def test_model_cannot_create_booking_without_server_confirmation(repository, seeded, llm_runtime):
    coordinator = EducationCoordinator(repository, SessionStore(), llm_runtime=llm_runtime, embedding_provider=FakeEmbeddingProvider())
    result = coordinator.process("family", "直接帮我下单")
    assert result["status"] != "confirmed"
    assert repository.list_bookings() == []
    assert "create_booking" not in coordinator.available_tool_names
```

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv/bin/pytest -q tests/test_agent_tools.py tests/test_agents.py`

Expected: FAIL because the tool registry and typed tool arguments do not exist.

- [ ] **Step 3: Implement typed read tools**

```python
@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    args_schema: type[BaseModel]
    handler: Callable[[BaseModel], dict]


class MatchTeachersArgs(BaseModel):
    student_id: int
    course_id: int
    campus_id: int
    start_at: datetime
    duration_minutes: int = Field(gt=0, le=360)
    preferred_teacher_id: int | None = None
```

`EducationTools` exposes lookup and matching methods. Returned data is JSON-safe, uses IDs from repository records, and contains no SQLAlchemy objects.

- [ ] **Step 4: Implement a bounded LangChain tool loop**

Convert each `AgentTool` to `StructuredTool`. Bind the list to `ChatOpenAI`, append `AIMessage` and `ToolMessage` values, cap execution at four steps, and return:

```python
@dataclass(frozen=True)
class ToolLoopResult:
    answer: str
    trace: tuple[str, ...]
```

Trace entries use only `tool_name: success|error|N candidates`. They never include tool arguments containing contact data or raw model reasoning.

- [ ] **Step 5: Verify tool and scheduling safety tests**

Run: `.venv/bin/pytest -q tests/test_agent_tools.py tests/test_agents.py tests/test_scheduling_service.py`

Expected: PASS; unconfirmed requests create zero bookings and confirmed requests still create exactly one.

- [ ] **Step 6: Commit**

```bash
git add agents/llm agents/education_tools.py agents/scheduling_agent.py tests/test_agent_tools.py tests/test_agents.py
git commit -m "feat: add guarded education agent tools"
```

---

### Task 4: FAISS knowledge retrieval and grounded LLM consultation

**Files:**
- Replace: `services/knowledge_service.py`
- Modify: `agents/consultant_agent.py`
- Modify: `agents/education_tools.py`
- Create: `tests/test_vector_knowledge.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: `EducationRepository.list_knowledge`, injected embedding provider, `LLMRuntime.tool_loop`.
- Produces: `VectorKnowledgeService.search(query, top_k, category) -> list[KnowledgeHit]`, `KnowledgeHit(id, content, category, score)`, and consultation responses with `sources`.

- [ ] **Step 1: Write failing vector ranking and grounded-answer tests**

```python
def test_vector_service_ranks_semantic_match(repository):
    repository.add_knowledge("课程开始前24小时可以免费取消。", "policy", ["取消"])
    repository.add_knowledge("浦东校区位于张江路。", "campus", ["地址"])
    service = VectorKnowledgeService(repository, FakeEmbeddingProvider())
    hits = service.search("临时有事怎么退课", top_k=1)
    assert hits[0].category == "policy"


def test_consultant_uses_search_tool_and_returns_sources(repository):
    runtime = FakeLLMRuntime(tool_answer="可提前24小时取消", tool_calls=["search_knowledge"])
    agent = ConsultantAgent(repository, runtime, FakeEmbeddingProvider())
    result = agent.process("怎么取消课程")
    assert result["answer"] == "可提前24小时取消"
    assert result["sources"][0]["category"] == "policy"
    assert result["tool_trace"] == ["search_knowledge: success"]
```

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv/bin/pytest -q tests/test_vector_knowledge.py tests/test_api.py::test_knowledge_search_uses_education_content`

Expected: FAIL because `VectorKnowledgeService` and `KnowledgeHit` do not exist.

- [ ] **Step 3: Implement injected FAISS retrieval**

```python
@dataclass(frozen=True)
class KnowledgeHit:
    id: int
    content: str
    category: str
    score: float
```

Normalize document and query vectors, use `faiss.IndexFlatIP`, and map row positions back to document IDs. Rebuild when the tuple `(id, updated_at)` changes. The production embedding provider wraps `SentenceTransformer("BAAI/bge-small-zh-v1.5")`; tests inject fixed vectors.

- [ ] **Step 4: Ground consultant answers through the actual search tool**

Create a per-request `search_knowledge` tool whose handler appends source metadata to a local collector. Call `runtime.tool_loop` with only this tool and a system instruction that forbids unsupported claims. Return the answer, deduplicated sources, and sanitized trace.

- [ ] **Step 5: Run vector, consultation, and API tests**

Run: `.venv/bin/pytest -q tests/test_vector_knowledge.py tests/test_api.py`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add services/knowledge_service.py agents/consultant_agent.py agents/education_tools.py tests/test_vector_knowledge.py tests/test_api.py
git commit -m "feat: restore FAISS grounded consultation"
```

---

### Task 5: Readiness, HTTP error mapping, and DeepSeek UI identity

**Files:**
- Modify: `api/education.py`
- Modify: `app.py`
- Modify: `web/templates/index.html`
- Modify: `web/static/styles.css`
- Modify: `tests/test_api.py`
- Modify: `tests/test_review_regressions.py`

**Interfaces:**
- Consumes: `LLMUnavailableError`, coordinator response metadata, vector service readiness.
- Produces: `GET /ready`, HTTP 503 mapping, visible model badge, separate student chat and admin sections.

- [ ] **Step 1: Write failing readiness, failure-mapping, and rendered-copy tests**

```python
def test_ready_reports_mandatory_llm_model(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "agent_mode": "llm", "model": "fake-deepseek"}


def test_chat_maps_model_outage_to_503(repository):
    runtime = FakeLLMRuntime(error=LLMUnavailableError("DeepSeek 服务暂时不可用"))
    client = TestClient(create_app(repository=repository, llm_runtime=runtime, embedding_provider=FakeEmbeddingProvider()))
    response = client.post("/api/chat", json={"message": "帮我排课"})
    assert response.status_code == 503
    assert response.json()["detail"] == "DeepSeek 服务暂时不可用"


def test_homepage_identifies_deepseek_agent(client):
    page = client.get("/")
    assert "DeepSeek LLM Agent" in page.text
    assert "规则引擎离线可用" not in page.text
```

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv/bin/pytest -q tests/test_api.py tests/test_review_regressions.py`

Expected: FAIL because `/ready`, 503 mapping, and DeepSeek page identity are absent.

- [ ] **Step 3: Implement readiness and stable error responses**

`/health` remains process liveness. `/ready` checks coordinator/runtime/vector service presence without making a paid model request. Map `LLMUnavailableError` to 503 and `AgentConfigurationError` to startup failure. Include `request_id`, `agent_mode`, `model`, and sanitized `tool_trace` in successful chat responses.

- [ ] **Step 4: Separate chat identity from administration UI**

Add a visible `DeepSeek LLM Agent · <model>` badge near the chat header. Move the existing forms under a collapsed or clearly separated “教务后台” section. Preserve safe `textContent` rendering and do not introduce `innerHTML`.

- [ ] **Step 5: Run API and XSS regression tests**

Run: `.venv/bin/pytest -q tests/test_api.py tests/test_review_regressions.py`

Expected: PASS, and `rg -n 'innerHTML|insertAdjacentHTML' web` returns no matches.

- [ ] **Step 6: Commit**

```bash
git add api/education.py app.py web tests/test_api.py tests/test_review_regressions.py
git commit -m "feat: expose mandatory DeepSeek agent readiness"
```

---

### Task 6: Dependencies, documentation, Skills, and complete verification

**Files:**
- Modify: `requirements.txt`
- Remove: `requirements-ai.txt`
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `DEV_SPEC.md`
- Modify: `.github/skills/setup-environment/SKILL.md`
- Modify: `.github/skills/setup-environment/scripts/setup.sh`
- Modify: `.github/skills/setup-environment/scripts/setup.ps1`
- Modify: `.github/skills/setup-environment/scripts/verify_env.py`
- Modify: `.github/skills/interview-prep/references/project_knowledge.md`
- Modify: `.github/skills/resume-writer/references/project_highlights.md`

**Interfaces:**
- Consumes: all completed runtime and Agent paths.
- Produces: one mandatory install path and accurate project claims; the static no-fallback guard created in Task 2 remains part of the full suite.

- [ ] **Step 1: Make LLM dependencies and configuration mandatory**

Merge these into `requirements.txt` and remove `requirements-ai.txt`:

```text
langchain-core>=0.3,<1.0
langchain-openai>=0.2,<1.0
faiss-cpu>=1.7
numpy>=1.21
sentence-transformers>=3.0
```

Rewrite `.env.example` with mandatory DeepSeek names and an empty `DEEPSEEK_API_KEY`. The setup verifier must report a clear failure when the key is absent; automated pytest remains keyless because it injects fakes.

- [ ] **Step 2: Update docs and project Skills to exact implemented claims**

README and DEV_SPEC must describe mandatory DeepSeek startup, actual tool selection, local FAISS, confirmation safety, and the separate manual smoke test. Remove “AI optional”, “offline rule mode”, and keyword-only knowledge claims. Skill references must distinguish the actual tool loop from deterministic scheduling rules and must not claim live DeepSeek verification unless it was run.

- [ ] **Step 3: Install, validate, and run complete verification**

Run:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/pytest -q
.venv/bin/python -m compileall -q agents api config db services web app.py
.venv/bin/python -m pip check
bash -n .github/skills/setup-environment/scripts/setup.sh
for skill in .github/skills/*; do .venv/bin/python .github/skills/skill-creator/scripts/quick_validate.py "$skill" || exit 1; done
git diff --check
rg -n 'innerHTML|insertAdjacentHTML' web
```

Expected: all tests and validators pass; the two final `rg` commands return no forbidden matches.

- [ ] **Step 6: Optional live smoke test with user-provided local key**

Run only when `DEEPSEEK_API_KEY` already exists in the local environment; never print it:

```bash
RUN_DEEPSEEK_SMOKE=1 .venv/bin/pytest -q tests/test_deepseek_smoke.py
```

Expected: one route/extraction/tool-response round trip succeeds. If the key is absent, report the skipped live verification without blocking offline acceptance.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "docs: make DeepSeek agent the required runtime"
```

---

## Final review and integration

- [ ] Run `git status --short --branch` and confirm only intentional changes are committed.
- [ ] Request an independent code review focused on mandatory-LLM enforcement, confirmation safety, tool data exposure, RAG grounding, and startup behavior.
- [ ] Fix all Critical and Important findings with failing regression tests first.
- [ ] Re-run the complete Task 6 verification commands.
- [ ] Push the feature branch and fast-forward `master` only after the merged result passes the full suite.
