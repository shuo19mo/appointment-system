# 当前项目源码锚点

## DeepSeek Agent 主链路

- `config/agent.py`：强制 `AGENT_MODE=llm`、`MODEL_PROVIDER=deepseek` 和非空 Key。
- `agents/llm/runtime.py`：DeepSeek 结构化输出、文本调用和最多 4 步的 LangChain 工具循环。
- `agents/coordinator.py`：先经 DeepSeek 路由，再进入排课或咨询 Agent，并附模型元数据。
- `agents/task_classification_agent.py`：`TaskRoute` 结构化分类，不使用关键词分支。
- `agents/scheduling/input_parser.py`：`SchedulingExtraction` 提取动作、时间和排课字段。
- `agents/session_store.py`：按 `session_id` 隔离的 TTL 会话。

需要讲清：生产聊天必须经过 LLM；自动化测试注入 Fake Runtime，不等于已验证真实线上 API。

## 工具与确认安全

- `agents/education_tools.py`：学生、校区、课程、教师和档期匹配的有类型只读工具。
- `agents/llm/tools.py`：`AgentTool` 契约。
- `agents/scheduling_agent.py`：候选先进入 `pending_booking`，用户确认后服务端才写库。
- 普通工具注册表没有 `create_booking`；最终写入只能回到 `SchedulingService`。
- tool trace 只保留工具名和状态，不暴露参数、联系方式或模型思维过程。

## 排课与数据一致性

- `services/scheduling_service.py`：教师硬约束、软排序和创建课程。
- `db/repositories/education_repository.py`：双方冲突查询、事务内二次检查、SQLite `BEGIN IMMEDIATE`。
- `db/models.py`：带时区输入统一转 UTC，读取恢复 aware UTC。

需要讲清：`start < existing_end AND end > existing_start`，相邻课程允许；资格、校区、可用时间和双方冲突是硬约束；指定教师、专长、偏好和负载只参与排序。

## FAISS RAG 边界

- `services/knowledge_service.py`：本地 Embedding、向量归一化和 `faiss.IndexFlatIP`；文档变更后重建。
- `agents/consultant_agent.py`：DeepSeek 必须通过 `search_knowledge` 工具读取资料，返回来源。
- 实时档期必须走 Repository / SchedulingService，不能由知识文本回答。

## 可验证证据

- `tests/test_llm_runtime.py`：强制配置与 runtime 注入。
- `tests/test_task_classification.py`、`tests/test_parser.py`：LLM 结构化路由和字段提取。
- `tests/test_agent_tools.py`：有界工具调用和无直接创建工具。
- `tests/test_agents.py`：匹配、确认、取消和未确认不写库。
- `tests/test_vector_knowledge.py`：FAISS 排序与 grounded 来源。
- `tests/test_scheduling_service.py`、`tests/test_review_regressions.py`：冲突、时区和并发。
- `tests/test_api.py`：`/health`、`/ready`、503 和页面身份。

## 声称边界

当前已实现：强制 DeepSeek 架构、结构化路由与提取、受限 LangChain 工具调用、FAISS RAG、会话隔离、确认门、排课确定性规则、SQLite 单库并发保护、管理 API 与 Fake provider 离线测试。

需要实测后再写：真实 DeepSeek API 调用成功、延迟、Token 成本和线上稳定性。

当前规划：Redis、PostgreSQL 排他约束、复杂权限、支付、班课、教室容量、生产机构数据和业务提升指标。
