# 多校区智能排课项目知识地图

共 24 个知识点。题号来自 `../../interview-prep/references/real_interview_questions.md`。

| 域 | ID | 知识点 | 当前源码 | 真题 |
|---|---|---|---|---|
| D1 定位与架构 | D1.1 | 业务痛点与 V1 边界 | `README.md`, `DEV_SPEC.md` | RQ01, RQ03 |
| | D1.2 | Web/API/Agent/Service/DB 分层 | `README.md`, `app.py` | RQ01 |
| | D1.3 | 应用装配与演示数据 | `app.py` | RQ02 |
| D2 Agent 与会话 | D2.1 | EducationCoordinator 路由 | `agents/coordinator.py` | RQ08, RQ09 |
| | D2.2 | DeepSeek 结构化任务路由 | `agents/task_classification_agent.py`, `agents/llm/runtime.py` | RQ08 |
| | D2.3 | 有界工具调用与确认门 | `agents/llm/runtime.py`, `agents/education_tools.py`, `agents/scheduling_agent.py` | RQ02, RQ08 |
| | D2.4 | session_id 隔离与 TTL | `agents/session_store.py` | RQ09 |
| D3 排课规则 | D3.1 | 半开区间冲突判定 | `db/repositories/education_repository.py` | RQ11 |
| | D3.2 | 课程资格、校区、档期硬约束 | `services/scheduling_service.py` | RQ11 |
| | D3.3 | 指定教师、专长和负载软排序 | `services/scheduling_service.py` | RQ11 |
| | D3.4 | 指定教师不可用与替代候选 | `services/scheduling_service.py`, `tests/test_scheduling_service.py` | RQ11 |
| D4 数据一致性 | D4.1 | 教师与学生双侧冲突 | `db/repositories/education_repository.py` | RQ11 |
| | D4.2 | 匹配后事务内二次检查 | `db/repositories/education_repository.py` | RQ14 |
| | D4.3 | SQLite `BEGIN IMMEDIATE` 并发保护与生产迁移边界 | `db/repositories/education_repository.py`, `db/db_router.py`, `README.md` | RQ14 |
| D5 解析与 API | D5.1 | DeepSeek 排课字段提取和缺失追问 | `agents/scheduling/input_parser.py`, `agents/scheduling/models.py` | RQ02 |
| | D5.2 | Pydantic 请求校验和 503/409/422 | `api/education.py` | RQ02 |
| | D5.3 | 匹配、创建、查询、取消接口 | `api/education.py` | RQ02 |
| D6 知识咨询 | D6.1 | 稳定知识与实时数据边界 | `services/knowledge_service.py`, `agents/consultant_agent.py` | RQ04 |
| | D6.2 | 本地 Embedding 与 FAISS 排序 | `services/knowledge_service.py`, `config/model_provider.py` | RQ13 |
| | D6.3 | Grounded 工具回答与来源 | `agents/consultant_agent.py`, `tests/test_vector_knowledge.py` | RQ04, RQ06, RQ13 |
| D7 测试评估 | D7.1 | LLM router/parser Fake 验收测试 | `tests/test_task_classification.py`, `tests/test_parser.py` | RQ11 |
| | D7.2 | 排课不变量测试 | `tests/test_scheduling_service.py` | RQ11 |
| | D7.3 | 工具、会话与 API 测试 | `tests/test_agent_tools.py`, `tests/test_sessions.py`, `tests/test_api.py` | RQ10, RQ11 |
| | D7.4 | Agent/RAG/性能指标设计 | `DEV_SPEC.md`, `README.md` | RQ06, RQ10, RQ11 |

推荐顺序：D2.1 → D2.2 → D2.3 → D5.1 → D3.1 → D3.2 → D4.2 → D6.2 → D6.3 → 其余条目。
