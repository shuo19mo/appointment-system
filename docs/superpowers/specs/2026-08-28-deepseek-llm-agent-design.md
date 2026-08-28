# 强制 DeepSeek LLM Agent 架构设计

## 1. 目标

在保留当前教育排课数据模型、冲突保护、API 和管理后台的前提下，恢复并升级旧项目的 LLM 主链路。运行中的聊天入口必须由 DeepSeek LLM 驱动，不允许静默降级为关键词分类或正则解析。

完成后，本项目应准确定位为“DeepSeek 驱动的多 Agent 教育排课系统”，而不是规则工作流套用 Agent 类名。

## 2. 不变约束

- 教师资格、服务校区、档期、教师冲突、学生冲突和最大日课时仍由确定性服务判断。
- LLM 不得绕过 `SchedulingService` 或直接写数据库。
- 创建排课必须建立在当前会话的待确认方案上，并收到用户明确确认。
- 时间继续统一持久化为 UTC，API 转换为 `Asia/Shanghai`。
- SQLite 继续使用 `BEGIN IMMEDIATE` 保护“冲突检查 + 创建”的原子流程。
- 真实 DeepSeek Key 只保存在 `.env` 或部署密钥服务中，不提交 Git、不返回前端、不写日志。

## 3. 运行模式与配置

系统仅提供 LLM 模式，不再把规则解析作为生产降级路径。

```env
AGENT_MODE=llm
MODEL_PROVIDER=deepseek
DEEPSEEK_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
```

`LLM_MODEL` 必须可配置，默认采用设计时 DeepSeek 官方支持 JSON Output 和 Tool Calls 的 `deepseek-v4-flash`。模型名称发生变化时只修改配置，不改 Agent 代码。

启动阶段必须验证：

1. `AGENT_MODE` 等于 `llm`。
2. `MODEL_PROVIDER` 等于 `deepseek`。
3. `DEEPSEEK_API_KEY` 非空。
4. LangChain/OpenAI-compatible 与 FAISS/本地 Embedding 依赖可导入。

缺少任一条件时启动失败，并输出不包含 Key 的明确配置错误。上游超时、限流或模型错误在请求边界返回 HTTP 503，禁止改走规则答案。

## 4. Agent 架构

```text
POST /api/chat
      ↓
EducationAgentCoordinator
      ↓
LLMTaskRouterAgent
      ├── scheduling → LLMSchedulingAgent
      │                  ├── LLM structured extraction
      │                  ├── student/course/campus lookup tools
      │                  ├── teacher matching tool
      │                  └── explicit confirmation → SchedulingService.create_booking
      ├── consultation → LLMConsultantAgent
      │                  ├── FAISS knowledge retrieval tool
      │                  └── grounded LLM answer with source IDs
      └── unsupported → LLM capability-boundary response
                              ↓
                  EducationRepository / SQLite
```

### 4.1 LLMTaskRouterAgent

- 使用 DeepSeek 判断 `scheduling`、`consultation`、`unsupported`。
- 输出采用严格 JSON Schema；无法解析时重试一次，仍失败则返回 503。
- 若会话已有待补充或待确认排课，短回复优先路由回 `scheduling`。
- 路由结果记录类别、耗时和 request ID，不记录完整用户隐私文本。

### 4.2 LLMSchedulingAgent

- 将当前会话状态和用户最新消息交给 DeepSeek，提取学生、校区、学科、年级、时间、时长和偏好教师。
- LLM 只能提交结构化候选字段；实体存在性和时间合法性由工具与 Pydantic 校验。
- 信息缺失时由 LLM 生成针对性追问，但追问依据来自结构化缺失字段。
- 信息完整后调用只读工具查询实体和教师候选，并返回可解释推荐理由。
- 候选方案写入服务端 `SessionStore.pending_booking`，其中保存候选教师 ID、课程、校区、学生、时间和时长。

### 4.3 确认门与写工具

- 写入工具不向普通规划步骤开放。
- 只有用户消息明确表达确认，并且当前 session 存在 `pending_booking` 时，Coordinator 才进入确认分支。
- 用户只能确认待选候选中的教师；LLM 不能自行替换教师 ID、时间或课程。
- 确认分支调用 `SchedulingService.create_booking`，服务在同一事务内重新检查冲突。
- 写入成功后清除 pending 状态；冲突则保留上下文并要求重新匹配。

### 4.4 LLMConsultantAgent 与 RAG

- 课程、教师、校区和政策文档使用本地中文 Embedding 建立 FAISS 索引。
- 检索工具返回 Top-K 内容、文档 ID、类别和相关度，不返回实时排课结果。
- DeepSeek 只能依据检索文档回答；没有相关文档时必须承认知识不足。
- API 返回 `sources`，支持前端显示回答依据。
- 实时档期、教师冲突和课程安排必须走数据库工具，不能来自向量文本。

## 5. 工具边界

Agent 可使用以下工具：

- `lookup_student(name)`：查询有效学生。
- `lookup_course(subject, grade)`：查询有效课程。
- `lookup_campus(name)`：查询有效校区。
- `lookup_teacher(name)`：查询指定教师。
- `match_teachers(student_id, course_id, campus_id, start_at, duration_minutes, preferred_teacher_id)`：调用确定性匹配服务。
- `search_knowledge(query, category, top_k)`：执行 FAISS 检索。

`create_booking` 和 `cancel_booking` 属于受保护动作：必须由 Coordinator 在确认/取消意图与服务端状态验证通过后调用，不能仅凭模型 tool call 执行。

## 6. 接口与前端

- `POST /api/chat` 保持现有请求格式，响应增加 `agent_mode`、`model`、`request_id` 和可选 `tool_trace`。
- `tool_trace` 只包含工具名称和业务状态，例如 `match_teachers: 2 candidates`，不暴露 Chain-of-Thought、prompt、Key 或模型原始内部推理。
- `/health` 表示进程存活；新增 `/ready` 表示 LLM 配置、索引和数据库是否就绪。
- 首页明确显示 `DeepSeek LLM Agent` 和当前模型，不再显示“规则引擎离线可用”。
- 学生聊天入口与教务资料维护在信息层级上分开，避免当前页面将营销首页、聊天和底层 ID 表单混为一体。

## 7. 错误策略

- 配置缺失：启动失败，错误类型 `AgentConfigurationError`。
- DeepSeek 超时、限流、鉴权或上游错误：返回 503 和稳定 `detail`，不泄露上游响应体。
- LLM JSON 不合法：有限重试后返回 503，不降级正则。
- 工具参数不合法：返回 422 或由 Agent 追问缺失字段。
- 资源不存在：返回 404 或聊天中的明确业务提示。
- 排课冲突：返回 409 或聊天中的冲突说明与重新匹配建议。

## 8. 测试策略

- 单元测试注入 `FakeChatModel` 和 `FakeEmbeddingProvider`，不访问网络、不消耗 DeepSeek 余额。
- 覆盖 LLM 路由、结构化提取、工具调用、RAG grounding、会话合并和确认门。
- 明确测试模型要求创建排课但用户未确认时，数据库不得新增记录。
- 保留现有时区、并发冲突、CRUD 和 API 回归测试。
- 增加带 `DEEPSEEK_API_KEY` 才运行的手动 smoke test，不纳入默认 CI。
- 验收时确认生产代码不存在规则分类/正则排课 fallback 的调用路径。

## 9. 依赖与迁移

- 核心运行依赖合并 LangChain OpenAI-compatible、FAISS 和本地中文 Embedding；由于 LLM 为强制能力，不再把它们描述为可选运行依赖。
- 保留依赖注入接口，使测试和未来模型迁移不绑定具体 SDK 实例。
- 数据库 Schema 无需回滚；现有 `KnowledgeDocument.embedding` 字段可继续使用。
- 首次启动构建或加载本地 FAISS 索引。索引失败时 readiness 失败，聊天接口不可用。

## 10. 验收标准

- 没有 `DEEPSEEK_API_KEY` 时应用明确拒绝启动。
- 有效配置下，任务分类、字段提取和回答生成均真实调用 DeepSeek。
- DeepSeek 至少完成一次实际工具选择；工具结果进入最终响应。
- 未经明确确认，任何模型输出都不能创建排课。
- 确认后仍通过确定性服务阻止教师和学生撞课。
- 课程政策回答来自 FAISS 检索文档并返回来源。
- 页面显示 DeepSeek Agent 模式和当前模型。
- 默认测试完全离线并全部通过；手动 DeepSeek smoke test可单独执行。
