# 当前项目亮点与源码锚点

## 1. 强制 DeepSeek Agent 编排

- `config/agent.py`：启动时校验 LLM 模式、DeepSeek provider 与 API Key。
- `agents/task_classification_agent.py`：DeepSeek `TaskRoute` 结构化路由。
- `agents/scheduling/input_parser.py`：DeepSeek `SchedulingExtraction` 多轮字段与动作提取。
- `agents/coordinator.py`：统一编排并返回模型和清洗后的 tool trace。

可信表达：将自然语言路由、相对时间与排课字段提取迁移到强制 DeepSeek 结构化输出，模型故障显式返回 503。自动化测试使用 Fake Runtime；未做真实 smoke test 时不能写线上模型已验证。

## 2. 有界工具调用与写入安全

- `agents/llm/runtime.py`：LangChain `StructuredTool` 循环，最多 4 步。
- `agents/education_tools.py`：真实学生、课程、校区、教师与档期匹配只读工具。
- `agents/scheduling_agent.py`：`pending_booking` 与服务端确认门。
- `tests/test_agent_tools.py`、`tests/test_agents.py`：无 `create_booking` 工具、未确认零写入、确认后单次写入。

可信表达：让模型动态选择只读工具，同时将数据库写入隔离到候选确认后的确定性服务；trace 不记录联系方式、完整参数或模型思维过程。

## 3. FAISS Grounded RAG

- `services/knowledge_service.py`：本地 Embedding、归一化向量、`faiss.IndexFlatIP` 与文档变更重建。
- `agents/consultant_agent.py`：只允许通过 `search_knowledge` 回答课程、教师、校区和政策，并返回来源。
- `tests/test_vector_knowledge.py`：语义排序、索引更新与来源验证。

可信表达：实现本地 Embedding + FAISS 教育知识检索，并约束 DeepSeek 基于工具结果生成答案；实时档期始终查询数据库。

## 4. 排课规则与事务一致性

- `services/scheduling_service.py`：课程资质、服务校区、可用时间、教师/学生冲突、偏好和负载排序。
- `db/repositories/education_repository.py`：事务内二次检查与 SQLite `BEGIN IMMEDIATE`。
- `db/models.py`：UTC 持久化与时区恢复。
- `tests/test_scheduling_service.py`、`tests/test_review_regressions.py`：重叠拒绝、相邻课程、跨偏移和并发占位。

可信表达：在单 SQLite 数据库内串行化“检查 + 创建”，用半开区间支持相邻课程。多实例生产仍需 PostgreSQL 排他约束。

## 5. 教育领域与 API

- `db/models.py`：Campus、Teacher、Course、TeacherCourse、TeacherCampus、TeacherAvailability、Student、ClassBooking、KnowledgeDocument。
- `api/education.py`：资料管理、候选匹配、课程安排、知识、聊天和 503 错误映射。
- `app.py`：`/health`、`/ready`、lifespan 依赖注入和无导入写库。
- `.github/skills/setup-environment/`：强制配置验证与无网络 smoke provider。

可信表达：将教师资质、校区、档期和课程安排拆分建模，提供 DeepSeek Agent 与教务管理 API；自动化测试数和通过状态必须现场运行后再写。

## 6. 规划边界

只能写为规划：MCP、流式响应、Redis 会话、PostgreSQL 排他约束、复杂长期记忆、反思自学习、班课、支付、生产客户与业务提升指标。
