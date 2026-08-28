# 多校区补习机构 DeepSeek 排课 Agent DEV SPEC

## 1. 产品定位

本系统面向多校区补习机构。学生、家长或教务通过自然语言提出排课与课程咨询需求；DeepSeek Agent 负责语义理解和受限工具选择，确定性业务服务负责实时校验和数据库写入。

## 2. V1 范围

V1 必须支持：

- 多校区、教师、课程、学生资料管理。
- 教师授课资格、服务校区和可用时间管理。
- 根据学科、年级、校区、时间和教师偏好匹配教师。
- 创建、查询、确认和取消一对一课程安排。
- 教师与学生双边时间冲突检查。
- 课程、校区、教师和机构政策的 FAISS RAG 咨询。
- 按 `session_id` 隔离多轮状态。
- 生产聊天强制使用 DeepSeek；配置或调用失败时显式失败。
- 自动化测试注入 Fake LLM / Embedding，不访问网络。

V1 不包含支付、班课、教室容量、考勤、复杂权限和第三方教务系统同步。

## 3. Agent 架构

`EducationCoordinator` 是统一入口：

1. `TaskClassificationAgent` 调用 DeepSeek 结构化输出，将请求路由到 `scheduling`、`consultation` 或 `unsupported`。
2. `SchedulingAgent` 使用 DeepSeek 提取 `action` 和排课字段，随后查询真实数据库并调用 `SchedulingService`。
3. `ConsultantAgent` 通过最多 4 步的 DeepSeek 工具循环调用 `search_knowledge`，只能依据 FAISS 返回资料回答。
4. 工具 trace 只包含工具名与 `success/error/N candidates`，不得包含 API Key、联系方式、完整参数、原始用户文本或模型思维过程。

生产路径不允许关键词分类、正则日期解析或规则聊天降级。模型不可用时返回稳定 503。

## 4. 强制运行配置

- `AGENT_MODE=llm`
- `MODEL_PROVIDER=deepseek`
- `DEEPSEEK_API_KEY` 非空
- `LLM_BASE_URL` 默认 `https://api.deepseek.com`
- `LLM_MODEL` 默认 `deepseek-v4-flash`
- 本地 Embedding 默认 `BAAI/bge-small-zh-v1.5`

应用模块导入不得验证密钥或创建数据库；FastAPI lifespan 在生产启动时创建真实 DeepSeek runtime 和本地 Embedding。测试通过 `create_app(..., llm_runtime=fake, embedding_provider=fake)` 注入。

## 5. 排课状态与确认门

`SchedulingExtraction` 输出：

- `action`: `schedule | confirm | cancel`
- `booking_id`
- `student_name`
- `campus_name`
- `subject`
- `grade`
- `start_at`
- `duration_minutes`
- `preferred_teacher_name`

缺少排课必填字段时返回明确追问。信息完整后只生成候选和 `pending_booking`。只有 DeepSeek 提取到 `confirm`，且当前 session 存在候选方案、教师属于候选列表时，服务端才调用 `SchedulingService.create_booking`。普通 Agent 工具不得注册 `create_booking`。

取消动作必须提取真实 `booking_id`；不存在时不修改数据库。

## 6. 排课确定性规则

候选教师必须：

1. 具备目标课程资格。
2. 服务目标校区。
3. 时间完整位于教师可用区间。
4. 与教师已有有效课程不重叠。
5. 与学生已有有效课程不重叠。

重叠使用半开区间 `start < existing_end AND end > existing_start`。软排序为指定教师 +100、专长 +20、学生偏好 +15、低负载最高 +10，最后按姓名和 ID 稳定排序。

创建时必须在事务中重新检查所有约束。SQLite 使用 `BEGIN IMMEDIATE` 串行化“检查 + 写入”；多实例生产应迁移 PostgreSQL 时间范围排他约束。

## 7. 知识检索边界

- `VectorKnowledgeService` 对 `KnowledgeDocument` 使用归一化向量和 `faiss.IndexFlatIP`。
- 文档 `(id, updated_at)` 集合变化时重建索引。
- RAG 只管理课程、教师简介、校区和政策。
- 实时教师档期和排课结果必须查询 Repository / SchedulingService。
- Consultation 回答返回文档 `id` 与 `category` 来源；检索不足时不得编造。

## 8. 领域与数据一致性

核心模型：`Campus`、`Teacher`、`Course`、`TeacherCourse`、`TeacherCampus`、`TeacherAvailability`、`Student`、`ClassBooking`、`KnowledgeDocument`。

- 会话由 `session_id` 隔离并按 TTL 清理。
- 时间输入必须带时区，持久化统一 UTC，API 输出转换为 `Asia/Shanghai`。
- 应用导入不自动创建 Schema 或写演示数据。
- 教育模型使用 clean-slate 数据库，不猜测迁移旧到店预约记录。

## 9. API 与错误

- `GET /health`：进程存活，不代表模型就绪。
- `GET /ready`：检查 runtime、coordinator 和向量服务存在，返回当前模型，不发送付费请求。
- `POST /api/chat`：返回 `session_id`、`request_id`、`agent_mode=llm`、`model` 和清洗后的 `tool_trace`。
- DeepSeek 调用失败：503。
- 资源不存在：404；业务冲突：409；输入无效：422。

管理 API 可直接维护资料和课程安排，但不是模型工具。

## 10. 验收标准

- 缺失或错误 DeepSeek 配置导致启动失败。
- 每个聊天请求先经过 LLM 路由；排课字段由 LLM 结构化提取。
- 受限工具循环真实执行数据库/FAISS 查询，最多 4 步。
- 未确认请求不能创建课程；确认后恰好创建一条。
- 教师和学生不能重叠排课，相邻课程允许。
- FAISS 能按语义排序知识，咨询答案带来源。
- 两个 session 上下文互不影响。
- 页面显示 DeepSeek Agent 身份并安全使用 `textContent`。
- pytest、编译、依赖、Shell、Skill 和 diff 检查全部通过。
- 只有执行过真实密钥 smoke test 时，文档或简历才可声称“已验证线上 DeepSeek 调用”。
